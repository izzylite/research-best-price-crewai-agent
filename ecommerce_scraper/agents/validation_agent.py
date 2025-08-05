"""ValidationAgent - Enhanced agent for validation, feedback loops, and persistent storage."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from pydantic import BaseModel
from ..config.settings import settings
from ..schemas.standardized_product import StandardizedProduct


class ValidationResult(BaseModel):
    """Pydantic model for validation task output."""
    validated_products: List[Dict[str, Any]]
    validation_summary: Dict[str, Any]
    feedback_required: bool = False
    feedback_data: Optional[Dict[str, Any]] = None


class ValidationAgent:
    """Enhanced agent for validation, feedback loops, and persistent JSON storage."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the validation agent with ProductDataValidator + File I/O operations."""
        # Handle both old (tools, llm) and new (stagehand_tool, verbose) calling patterns
        if stagehand_tool is not None:
            # New Flow-based calling pattern
            tools = [stagehand_tool] if stagehand_tool else []
        elif tools is None:
            tools = []
        
        agent_config = {
            "role": "StandardizedProduct Data Validation, Feedback & Storage Expert",
            "goal": """
            Validate extracted product data against StandardizedProduct schema, provide feedback
            to ExtractionAgent for re-extraction when needed, and manage persistent storage with
            JSON file operations, backup creation, and session accumulation across pages.
            """,
            "backstory": """
            You are a comprehensive data validation and storage expert responsible for ensuring
            data quality and managing persistent storage across multi-page scraping sessions.
            You never extract data yourself - you only validate, provide feedback, and store data.
            
            Your core expertise includes:
            - StandardizedProduct schema validation and compliance
            - Feedback generation for ExtractionAgent re-extraction requests
            - JSON file management with atomic updates and backup creation
            - Session-based data accumulation across multiple pages
            - Cross-page duplicate detection and removal
            - UK retail data standardization (GBP pricing, weights, etc.)
            - Multi-vendor data consistency across ASDA, Tesco, Waitrose, etc.
            - Price format validation and currency standardization
            - URL validation and image link verification
            - Text cleaning and normalization for UK product data
            - Data completeness assessment and quality scoring
            - Persistent storage with recovery capabilities
            
            CRITICAL: You focus on validation, feedback, and storage. You never extract data
            from web pages - that's the ExtractionAgent's job. You validate what they extract
            and provide feedback for improvement when needed.
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 3,
            "memory": settings.enable_crew_memory
        }

        if llm:
            agent_config["llm"] = llm

        self.agent = Agent(**agent_config)

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    def create_validation_task(self, vendor: str, category: str, products: List, page_number: int = 1, **kwargs):
        """Alias for create_validation_and_storage_task to match Flow calling pattern."""
        return self.create_validation_and_storage_task(
            vendor=vendor,
            category=category,
            page_number=page_number,
            session_id=kwargs.get('session_id'),
            max_retries=kwargs.get('max_retries', 3)
        )

    def create_validation_and_storage_task(self, 
                                         vendor: str, 
                                         category: str, 
                                         page_number: int = 1,
                                         session_id: str = None,
                                         max_retries: int = 3):
        """Create a task for validating data and managing persistent storage."""
        from crewai import Task

        task_description = f"""
        Validate extracted product data and manage persistent JSON storage with feedback loops.
        
        Vendor: {vendor}
        Category: {category}
        Page Number: {page_number}
        Session ID: {session_id}
        Max Re-extraction Retries: {max_retries}

        VALIDATION AND STORAGE WORKFLOW:
        1. **Receive extracted product batch from ExtractionAgent**
        2. **Validate each product against StandardizedProduct schema**
        3. **Decision Point:**
           - If validation passes: Save to JSON file and continue
           - If validation fails: Generate feedback for re-extraction
        4. **Manage persistent storage with session accumulation**
        5. **Handle deduplication across pages**
        6. **Update session statistics and progress**

        STANDARDIZEDPRODUCT SCHEMA VALIDATION:
        Required Fields:
        - name: Non-empty string, min 1 character
        - description: Non-empty string, min 1 character  
        - price.amount: Valid float > 0
        - price.currency: Must be "GBP" for UK retailers
        - image_url: Valid URL format
        - category: Must match "{category}"
        - vendor: Must match "{vendor}"
        - scraped_at: Valid ISO timestamp

        Optional Fields:
        - weight: Valid weight string with units (null if not available)

        FEEDBACK GENERATION CRITERIA:
        Generate re-extraction feedback if:
        - >20% of products missing required fields
        - >30% of products have invalid data formats
        - <5 products extracted when more are visible
        - Critical data quality issues detected

        FEEDBACK FORMAT:
        {{
          "validation_result": "failed",
          "feedback": {{
            "issues": [
              "Missing product descriptions for 5 products",
              "Invalid price format for 2 products"
            ],
            "suggestions": [
              "Look for description in product subtitle or details",
              "Check for alternative price selectors"
            ]
          }},
          "retry_count": 1,
          "max_retries": {max_retries}
        }}

        JSON FILE MANAGEMENT:
        - File Location: ./results/scraping_sessions/
        - File Name: {vendor}_{category}_{session_id}.json
        - Atomic Updates: Create backup before updating
        - Session Accumulation: Merge products across pages
        - Deduplication: Remove duplicates based on name + price + vendor

        CRITICAL: Focus on validation quality and storage reliability.
        Provide specific, actionable feedback for re-extraction when needed.

        ABSOLUTELY FORBIDDEN - JSON COMMENTS:
        - NEVER add // comments in JSON output
        - NEVER add "// Additional products omitted for brevity"
        - NEVER add "// Array of products" or similar comments
        - JSON must be valid and parseable - no comments allowed
        - Comments break JSON parsing and cause system failures
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Validation and storage result:
            {{
              "validation_complete": true,
              "products_saved": <number_of_valid_products_saved>,
              "products_failed": <number_of_invalid_products>,
              "feedback_required": <true/false>,
              "feedback_data": {{

              }},
              "storage_info": {{
                "json_file_path": "./results/scraping_sessions/{vendor}_{category}_{session_id}.json",
                "backup_created": <true/false>,
                "total_products_in_session": <accumulated_products>,
                "duplicates_removed": <number_of_duplicates>
              }},
              "session_stats": {{
                "total_pages_processed": {page_number},
                "total_products_saved": <accumulated_count>,
                "validation_success_rate": <percentage>,
                "ready_for_pagination": <true/false>
              }}
            }}
            
            If feedback_required is true, include detailed feedback for ExtractionAgent.
            If validation passes, confirm products are saved to persistent storage.
            """
        )

    def create_feedback_generation_task(self, 
                                      validation_issues: List[str],
                                      extraction_metadata: Dict[str, Any],
                                      retry_count: int = 1,
                                      max_retries: int = 3):
        """Create a task for generating specific feedback for re-extraction."""
        from crewai import Task

        task_description = f"""
        Generate specific, actionable feedback for ExtractionAgent re-extraction.
        
        Validation Issues: {validation_issues}
        Extraction Metadata: {extraction_metadata}
        Retry Count: {retry_count} of {max_retries}

        FEEDBACK GENERATION REQUIREMENTS:
        1. **Analyze specific validation failures**
        2. **Identify root causes of extraction issues**
        3. **Generate actionable improvement suggestions**
        4. **Provide alternative extraction strategies**
        5. **Specify quality requirements for re-extraction**

        ISSUE ANALYSIS:
        - Categorize validation failures by type
        - Identify patterns in missing or invalid data
        - Determine if issues are systematic or isolated
        - Assess extraction method effectiveness

        SUGGESTION GENERATION:
        - Provide specific selector alternatives
        - Suggest different extraction approaches
        - Recommend data cleaning improvements
        - Offer quality verification steps

        FEEDBACK QUALITY:
        - Be specific and actionable
        - Focus on fixable issues
        - Provide clear improvement guidance
        - Include success criteria for re-extraction

        CRITICAL: Generate feedback that leads to measurable improvement.
        Focus on the most impactful changes for data quality enhancement.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Detailed feedback for re-extraction:
            {{
              "validation_result": "failed",
              "feedback": {{
                "issues": [

                ],
                "suggestions": [

                ],
                "alternative_strategies": [

                ],
                "quality_requirements": {{

                }}
              }},
              "retry_count": {retry_count},
              "max_retries": {max_retries},
              "improvement_focus": "Primary areas for extraction improvement"
            }}
            
            Provide specific, actionable feedback that addresses root causes.
            """
        )

    def create_json_storage_task(self,
                               vendor: str,
                               category: str,
                               session_id: str,
                               products_to_save: List[Dict[str, Any]],
                               page_number: int = 1):
        """Create a task for managing JSON file storage and session accumulation."""
        from crewai import Task

        task_description = f"""
        Manage persistent JSON storage with session accumulation and backup creation.

        Vendor: {vendor}
        Category: {category}
        Session ID: {session_id}
        Products to Save: {len(products_to_save)} products
        Page Number: {page_number}

        JSON STORAGE REQUIREMENTS:
        1. **Create or update session JSON file**
        2. **Implement atomic file operations with backup**
        3. **Accumulate products across multiple pages**
        4. **Handle deduplication within session**
        5. **Update session metadata and statistics**

        FILE STRUCTURE:
        {{
          "scraping_session": {{
            "session_id": "{session_id}",
            "vendor": "{vendor}",
            "category": "{category}",
            "started_at": "ISO timestamp",
            "last_updated": "ISO timestamp",
            "status": "in_progress",
            "pagination_info": {{
              "total_pages_processed": {page_number},
              "current_page": {page_number}
            }}
          }},
          "products": [

          ],
          "session_statistics": {{
            "total_products_found": <count>,
            "total_products_validated": <count>,
            "validation_success_rate": <percentage>
          }}
        }}

        ATOMIC OPERATIONS:
        1. Create backup of existing file (if exists)
        2. Read current session data
        3. Merge new products with existing
        4. Remove duplicates based on name + price + vendor
        5. Update session metadata
        6. Write to temporary file
        7. Rename temporary file to final name
        8. Verify write success

        DEDUPLICATION STRATEGY:
        - Compare products by: name + price.amount + vendor
        - Keep most recent version of duplicates
        - Log duplicate removal for tracking

        CRITICAL: Ensure data integrity and atomic file operations.
        Never lose existing data during updates.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            JSON storage completion report:
            {{
              "storage_complete": true,
              "file_info": {{
                "file_path": "./results/scraping_sessions/{vendor}_{category}_{session_id}.json",
                "backup_created": <true/false>,
                "file_size_bytes": <file_size>,
                "write_successful": true
              }},
              "data_info": {{
                "products_added": <new_products_count>,
                "products_updated": <updated_products_count>,
                "duplicates_removed": <duplicate_count>,
                "total_products_in_session": <total_count>
              }},
              "session_updated": {{
                "pages_processed": {page_number},
                "last_updated": "ISO timestamp",
                "status": "in_progress"
              }}
            }}

            Confirm successful atomic storage operation with data integrity.
            """
        )

    def create_deduplication_task(self,
                                products: List[Dict[str, Any]],
                                existing_products: List[Dict[str, Any]] = None):
        """Create a task for comprehensive product deduplication."""
        from crewai import Task

        existing_count = len(existing_products) if existing_products else 0

        task_description = f"""
        Perform comprehensive deduplication across product datasets.

        New Products: {len(products)} products
        Existing Products: {existing_count} products
        Total to Process: {len(products) + existing_count} products

        DEDUPLICATION STRATEGY:
        1. **Primary matching**: name + price.amount + vendor
        2. **Secondary matching**: Similar names (fuzzy matching) + vendor
        3. **Tertiary matching**: Same image_url + vendor
        4. **Keep most recent**: Prefer products with later scraped_at timestamps

        MATCHING CRITERIA:
        - Exact match: Identical name, price, and vendor
        - Fuzzy match: >90% name similarity + same vendor + similar price (±5%)
        - Image match: Same image_url + same vendor
        - Category match: Same category + vendor + similar name

        DEDUPLICATION PROCESS:
        1. Group products by potential duplicates
        2. Apply matching criteria in priority order
        3. Select best representative from each group
        4. Preserve most complete product data
        5. Log all deduplication decisions

        QUALITY PRESERVATION:
        - Keep products with more complete data
        - Prefer products with descriptions over those without
        - Maintain products with valid image URLs
        - Preserve weight information when available

        CRITICAL: Maintain data quality while removing true duplicates.
        Err on the side of keeping products rather than over-deduplicating.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Deduplication completion report:
            {{
              "deduplication_complete": true,
              "deduplication_stats": {{
                "input_products": {len(products) + existing_count},
                "output_products": <final_unique_count>,
                "duplicates_removed": <removed_count>,
                "deduplication_rate": <percentage>
              }},
              "matching_breakdown": {{
                "exact_matches": <count>,
                "fuzzy_matches": <count>,
                "image_matches": <count>,
                "no_matches": <count>
              }},
              "deduplicated_products": [

              ]
            }}

            Return only unique products with highest quality data preserved.
            """
        )
