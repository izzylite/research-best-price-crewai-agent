"""Batch processing system for multi-vendor ecommerce scraping."""

import logging
import threading
import queue
import time
from typing import Dict, Any, List, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from ..state.state_manager import PaginationState, StateManager
from ..schemas.standardized_product import StandardizedProduct

logger = logging.getLogger(__name__)


@dataclass
class BatchJob:
    """Represents a batch scraping job."""
    job_id: str
    url: str
    vendor: str
    category: str
    session_id: str
    max_retries: int = 3
    retry_count: int = 0
    status: str = "pending"
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None


class BatchProcessor:
    """Manages batch processing of scraping jobs."""
    
    def __init__(self, scraper, state_manager: StateManager, num_workers: int = 3):
        """Initialize batch processor.
        
        Args:
            scraper: EcommerceScraper instance
            state_manager: StateManager instance
            num_workers: Number of worker threads
        """
        self.scraper = scraper
        self.state_manager = state_manager
        self.num_workers = num_workers
        
        self.job_queue = queue.Queue()
        self.jobs: Dict[str, BatchJob] = {}
        self.workers: List[threading.Thread] = []
        self.stop_event = threading.Event()
        
        # Progress tracking
        self.total_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0
        
        # Thread-safe job results
        self._results_lock = threading.Lock()
        self.results: Dict[str, List[StandardizedProduct]] = {}
    
    def add_job(self, job_id: str, url: str, vendor: str, category: str, session_id: str):
        """Add a new job to the queue.
        
        Args:
            job_id: Unique job identifier
            url: URL to scrape
            vendor: Vendor identifier
            category: Category identifier
            session_id: Session identifier
        """
        job = BatchJob(
            job_id=job_id,
            url=url,
            vendor=vendor,
            category=category,
            session_id=session_id
        )
        
        self.jobs[job_id] = job
        self.job_queue.put(job)
        self.total_jobs += 1
        
        logger.info(f"Added URL-based job: {job_id} for {vendor}/{category}")
    
    def start_workers(self):
        """Start worker threads."""
        for i in range(self.num_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(i,),
                name=f"BatchWorker-{i}"
            )
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
            logger.info(f"Worker {i} started")
        
        logger.info(f"Started {self.num_workers} batch processing workers")
    
    def stop_workers(self):
        """Stop all worker threads."""
        self.stop_event.set()
        
        # Wait for all workers to finish
        for worker in self.workers:
            worker.join()
        
        logger.info("Stopped batch processing")
    
    def _worker_loop(self, worker_id: int):
        """Main worker thread loop.
        
        Args:
            worker_id: Worker identifier
        """
        while not self.stop_event.is_set():
            try:
                # Get job with timeout to allow checking stop_event
                try:
                    job = self.job_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                logger.info(f"Worker {worker_id} processing job: {job.job_id}")
                
                # Get pagination state
                state = self.state_manager.get_pagination_state(
                    job.session_id, job.vendor, job.category
                )
                
                if not state:
                    # Create new state if doesn't exist
                    state = self.state_manager.create_pagination_state(
                        job.session_id, job.vendor, job.category
                    )
                
                logger.info(f"Worker {worker_id} scraping URL: {job.url}")
                
                try:
                    # Execute scraping
                    result = self.scraper.scrape_url(job.url)
                    
                    # Update state
                    if result.get("success"):
                        products = result.get("products", [])
                        state.update_progress(len(products), job.url)
                        state.mark_complete()  # Mark this URL as completed
                        
                        # Store results
                        with self._results_lock:
                            if job.job_id not in self.results:
                                self.results[job.job_id] = []
                            self.results[job.job_id].extend(products)
                        
                        job.status = "completed"
                        self.completed_jobs += 1
                        
                    else:
                        raise Exception(result.get("error", "Unknown error"))
                    
                except Exception as e:
                    logger.error(f"Worker {worker_id} error scraping URL {job.url}: {e}")
                    
                    # Handle retry logic
                    if job.retry_count < job.max_retries:
                        job.retry_count += 1
                        job.status = "retrying"
                        logger.info(f"Retrying job {job.job_id} (attempt {job.retry_count})")
                        self.job_queue.put(job)
                    else:
                        job.status = "failed"
                        job.error = str(e)
                        self.failed_jobs += 1
                        logger.error(f"Job {job.job_id} failed: {e}")
                
                finally:
                    self.job_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                continue
    
    def wait_completion(self):
        """Wait for all jobs to complete."""
        self.job_queue.join()
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information.
        
        Returns:
            Progress information dictionary
        """
        return {
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "failed_jobs": self.failed_jobs,
            "active_jobs": len(self.jobs) - (self.completed_jobs + self.failed_jobs),
            "success_rate": self.completed_jobs / max(self.total_jobs, 1) * 100
        }
    
    def get_results(self, job_id: str) -> List[StandardizedProduct]:
        """Get results for a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            List of scraped products
        """
        with self._results_lock:
            return self.results.get(job_id, [])