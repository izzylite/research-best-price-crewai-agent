"""Batch processing system for multi-vendor ecommerce scraping with producer-consumer pattern."""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Event
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum

from ecommerce_scraper.state.state_manager import StateManager, PaginationState, SessionStatus
from ecommerce_scraper.schemas.standardized_product import StandardizedProduct, ProductBatch
from ecommerce_scraper.config.sites import get_site_config_by_vendor

logger = logging.getLogger(__name__)


class BatchJobStatus(str, Enum):
    """Batch job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class BatchJob:
    """Represents a single scraping job for a vendor/category combination."""
    
    job_id: str
    session_id: str
    vendor: str
    category: str
    max_pages: Optional[int] = None
    priority: int = 1  # 1 = high, 2 = medium, 3 = low
    status: BatchJobStatus = BatchJobStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    products_scraped: int = 0
    pages_processed: int = 0
    retry_count: int = 0
    max_retries: int = 3
    
    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        for field in ['created_at', 'started_at', 'completed_at']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchJob':
        """Create from dictionary with proper deserialization."""
        # Convert ISO strings back to datetime objects
        for field in ['created_at', 'started_at', 'completed_at']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Convert string enums back to enum objects
        if 'status' in data:
            data['status'] = BatchJobStatus(data['status'])
        
        return cls(**data)


class BatchProcessor:
    """Producer-consumer batch processing system for multi-vendor scraping."""
    
    def __init__(self, 
                 max_workers: int = 3,
                 max_concurrent_vendors: int = 2,
                 output_dir: str = "./scraping_output",
                 state_manager: Optional[StateManager] = None):
        """Initialize batch processor.
        
        Args:
            max_workers: Maximum number of worker threads
            max_concurrent_vendors: Maximum vendors to scrape simultaneously
            output_dir: Directory for output files
            state_manager: State manager instance
        """
        self.max_workers = max_workers
        self.max_concurrent_vendors = max_concurrent_vendors
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.state_manager = state_manager or StateManager()
        
        # Job management
        self.job_queue = Queue()
        self.active_jobs: Dict[str, BatchJob] = {}
        self.completed_jobs: List[BatchJob] = []
        self.failed_jobs: List[BatchJob] = {}
        
        # Worker management
        self.workers: List[Thread] = []
        self.stop_event = Event()
        self.pause_event = Event()
        
        # Progress tracking
        self.progress_callback: Optional[Callable] = None
        self.vendor_semaphores: Dict[str, asyncio.Semaphore] = {}
        
        # Statistics
        self.stats = {
            "total_jobs": 0,
            "completed_jobs": 0,
            "failed_jobs": 0,
            "total_products": 0,
            "total_pages": 0,
            "start_time": None,
            "end_time": None
        }
    
    def add_job(self, vendor: str, category: str, max_pages: Optional[int] = None, 
                priority: int = 1, session_id: Optional[str] = None) -> str:
        """Add a scraping job to the queue.
        
        Args:
            vendor: Vendor identifier
            category: Category to scrape
            max_pages: Maximum pages to scrape
            priority: Job priority (1=high, 2=medium, 3=low)
            session_id: Session ID (will create if not provided)
            
        Returns:
            Job ID
        """
        if session_id is None:
            session_id = self.state_manager.create_session()
        
        job_id = f"{vendor}_{category}_{int(time.time())}"
        
        job = BatchJob(
            job_id=job_id,
            session_id=session_id,
            vendor=vendor,
            category=category,
            max_pages=max_pages,
            priority=priority
        )
        
        # Add to queue with priority (lower number = higher priority)
        self.job_queue.put((priority, job))
        self.stats["total_jobs"] += 1
        
        logger.info(f"Added job: {job_id} - {vendor}/{category}")
        return job_id
    
    def add_batch_jobs(self, jobs: List[Dict[str, Any]], session_id: Optional[str] = None) -> List[str]:
        """Add multiple jobs to the queue.
        
        Args:
            jobs: List of job specifications
            session_id: Session ID for all jobs
            
        Returns:
            List of job IDs
        """
        if session_id is None:
            session_id = self.state_manager.create_session()
        
        job_ids = []
        for job_spec in jobs:
            job_id = self.add_job(
                vendor=job_spec["vendor"],
                category=job_spec["category"],
                max_pages=job_spec.get("max_pages"),
                priority=job_spec.get("priority", 1),
                session_id=session_id
            )
            job_ids.append(job_id)
        
        return job_ids
    
    def start_processing(self, progress_callback: Optional[Callable] = None):
        """Start the batch processing workers.
        
        Args:
            progress_callback: Optional callback for progress updates
        """
        if self.workers:
            logger.warning("Batch processing already started")
            return
        
        self.progress_callback = progress_callback
        self.stop_event.clear()
        self.pause_event.clear()
        self.stats["start_time"] = datetime.now(timezone.utc)
        
        # Start worker threads
        for i in range(self.max_workers):
            worker = Thread(target=self._worker_loop, args=(i,), daemon=True)
            worker.start()
            self.workers.append(worker)
        
        logger.info(f"Started {self.max_workers} batch processing workers")
    
    def stop_processing(self):
        """Stop all batch processing workers."""
        self.stop_event.set()
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=30)
        
        self.workers.clear()
        self.stats["end_time"] = datetime.now(timezone.utc)
        
        logger.info("Stopped batch processing")
    
    def pause_processing(self):
        """Pause batch processing."""
        self.pause_event.set()
        logger.info("Paused batch processing")
    
    def resume_processing(self):
        """Resume batch processing."""
        self.pause_event.clear()
        logger.info("Resumed batch processing")
    
    def _worker_loop(self, worker_id: int):
        """Main worker loop for processing jobs.
        
        Args:
            worker_id: Worker identifier
        """
        logger.info(f"Worker {worker_id} started")
        
        while not self.stop_event.is_set():
            try:
                # Check if paused
                if self.pause_event.is_set():
                    time.sleep(1)
                    continue
                
                # Get next job from queue
                try:
                    priority, job = self.job_queue.get(timeout=5)
                except Empty:
                    continue
                
                # Check vendor concurrency limit
                if not self._can_process_vendor(job.vendor):
                    # Put job back in queue and wait
                    self.job_queue.put((priority, job))
                    time.sleep(2)
                    continue
                
                # Process the job
                self._process_job(job, worker_id)
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                time.sleep(5)
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _can_process_vendor(self, vendor: str) -> bool:
        """Check if we can process another job for this vendor.
        
        Args:
            vendor: Vendor identifier
            
        Returns:
            True if vendor can be processed
        """
        # Count active jobs for this vendor
        active_vendor_jobs = sum(
            1 for job in self.active_jobs.values() 
            if job.vendor == vendor and job.status == BatchJobStatus.RUNNING
        )
        
        return active_vendor_jobs < self.max_concurrent_vendors
    
    def _process_job(self, job: BatchJob, worker_id: int):
        """Process a single scraping job.
        
        Args:
            job: Job to process
            worker_id: Worker identifier
        """
        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        self.active_jobs[job.job_id] = job
        
        logger.info(f"Worker {worker_id} processing job: {job.job_id}")
        
        try:
            # Get or create pagination state
            state = self.state_manager.get_pagination_state(
                job.session_id, job.vendor, job.category
            )
            
            if state is None:
                state = self.state_manager.create_pagination_state(
                    job.session_id, job.vendor, job.category, job.max_pages
                )
            
            # Process the scraping job
            products = self._scrape_vendor_category(job, state, worker_id)
            
            # Save results
            self._save_job_results(job, products)
            
            # Update job status
            job.status = BatchJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.products_scraped = len(products)
            
            # Update statistics
            self.stats["completed_jobs"] += 1
            self.stats["total_products"] += len(products)
            self.stats["total_pages"] += job.pages_processed
            
            # Mark pagination state as completed
            self.state_manager.complete_pagination_state(
                job.session_id, job.vendor, job.category
            )
            
            logger.info(f"Completed job: {job.job_id} - {len(products)} products")
            
        except Exception as e:
            logger.error(f"Job {job.job_id} failed: {e}")
            
            job.status = BatchJobStatus.FAILED
            job.error_message = str(e)
            job.retry_count += 1
            
            # Retry logic
            if job.retry_count <= job.max_retries:
                logger.info(f"Retrying job {job.job_id} (attempt {job.retry_count})")
                # Put back in queue with lower priority
                self.job_queue.put((job.priority + 1, job))
                job.status = BatchJobStatus.PENDING
            else:
                self.stats["failed_jobs"] += 1
                self.failed_jobs.append(job)
        
        finally:
            # Remove from active jobs
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            
            # Add to completed jobs if successful
            if job.status == BatchJobStatus.COMPLETED:
                self.completed_jobs.append(job)
            
            # Notify progress callback
            if self.progress_callback:
                self.progress_callback(job, self.get_progress_summary())
    
    def _scrape_vendor_category(self, job: BatchJob, state: PaginationState, worker_id: int) -> List[StandardizedProduct]:
        """Scrape products for a specific vendor/category.
        
        Args:
            job: Batch job
            state: Pagination state
            worker_id: Worker identifier
            
        Returns:
            List of scraped products
        """
        # This is a placeholder - in real implementation, this would use
        # the actual scraping agents and tools
        
        products = []
        
        # Simulate scraping process
        site_config = get_site_config_by_vendor(job.vendor)
        
        # Process pages
        while not state.is_complete() and not self.stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(1)
                continue
            
            logger.info(f"Worker {worker_id} scraping {job.vendor}/{job.category} page {state.current_page}")
            
            # Simulate page scraping (replace with actual scraping logic)
            page_products = self._simulate_page_scraping(job.vendor, job.category, state.current_page)
            products.extend(page_products)
            
            # Update state
            state.update_progress(len(page_products))
            state.advance_page()
            job.pages_processed = state.current_page
            
            # Save state
            self.state_manager.update_pagination_state(state)
            
            # Respect rate limiting
            time.sleep(site_config.delay_between_requests)
        
        return products
    
    def _simulate_page_scraping(self, vendor: str, category: str, page: int) -> List[StandardizedProduct]:
        """Simulate scraping a page of products.
        
        This is a placeholder method that would be replaced with actual scraping logic.
        """
        # Simulate some products
        products = []
        for i in range(5):  # Simulate 5 products per page
            product = StandardizedProduct(
                name=f"{vendor.title()} {category} Product {page}-{i}",
                description=f"Sample product from {vendor} in {category} category",
                price={"amount": 10.99 + i, "currency": "GBP"},
                image_url=f"https://example.com/image_{page}_{i}.jpg",
                category=category,
                vendor=vendor,
                weight=f"{100 + i * 10}g"
            )
            products.append(product)
        
        # Simulate processing time
        time.sleep(2)
        
        return products
    
    def _save_job_results(self, job: BatchJob, products: List[StandardizedProduct]):
        """Save job results to file.
        
        Args:
            job: Completed job
            products: Scraped products
        """
        # Create output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{job.vendor}_{job.category}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # Prepare data for saving
        batch = ProductBatch(
            products=products,
            metadata={
                "job_id": job.job_id,
                "session_id": job.session_id,
                "vendor": job.vendor,
                "category": job.category,
                "pages_processed": job.pages_processed,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "total_products": len(products)
            }
        )
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(batch.model_dump(), f, indent=2, default=str)
        
        logger.info(f"Saved {len(products)} products to {filepath}")
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """Get current progress summary.
        
        Returns:
            Progress summary dictionary
        """
        total_jobs = self.stats["total_jobs"]
        completed = self.stats["completed_jobs"]
        failed = self.stats["failed_jobs"]
        active = len(self.active_jobs)
        pending = total_jobs - completed - failed - active
        
        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed,
            "failed_jobs": failed,
            "active_jobs": active,
            "pending_jobs": pending,
            "total_products": self.stats["total_products"],
            "total_pages": self.stats["total_pages"],
            "start_time": self.stats["start_time"],
            "active_job_details": [
                {
                    "job_id": job.job_id,
                    "vendor": job.vendor,
                    "category": job.category,
                    "pages_processed": job.pages_processed,
                    "products_scraped": job.products_scraped
                }
                for job in self.active_jobs.values()
            ]
        }
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job status dictionary or None if not found
        """
        # Check active jobs
        if job_id in self.active_jobs:
            return self.active_jobs[job_id].to_dict()
        
        # Check completed jobs
        for job in self.completed_jobs:
            if job.job_id == job_id:
                return job.to_dict()
        
        # Check failed jobs
        for job in self.failed_jobs:
            if job.job_id == job_id:
                return job.to_dict()
        
        return None
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if job was cancelled
        """
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            job.status = BatchJobStatus.CANCELLED
            logger.info(f"Cancelled job: {job_id}")
            return True
        
        return False
    
    def cleanup_completed_jobs(self, older_than_hours: int = 24):
        """Clean up old completed jobs.
        
        Args:
            older_than_hours: Remove jobs completed more than this many hours ago
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
        
        # Filter completed jobs
        self.completed_jobs = [
            job for job in self.completed_jobs
            if job.completed_at and job.completed_at > cutoff_time
        ]
        
        # Filter failed jobs
        self.failed_jobs = [
            job for job in self.failed_jobs
            if job.started_at and job.started_at > cutoff_time
        ]
        
        logger.info(f"Cleaned up jobs older than {older_than_hours} hours")
