"""NavigationAgent - Specialized agent for site navigation, popup handling, and pagination."""

from typing import List, Optional, Dict, Any
from crewai import Agent, LLM
from ..config.settings import settings
from ..config.sites import get_site_config_by_vendor, SiteConfig
from ..utils.popup_handler import PopupHandler


class NavigationAgent:
    """Specialized agent for ecommerce site navigation and pagination handling."""

    def __init__(self, stagehand_tool=None, verbose: bool = True, tools: List = None, llm: Optional[LLM] = None):
        """Initialize the navigation agent with StagehandTool only."""
        # Handle both old (tools, llm) and new (stagehand_tool, verbose) calling patterns
        if stagehand_tool is not None:
            # New Flow-based calling pattern
            tools = [stagehand_tool] if stagehand_tool else []
        elif tools is None:
            tools = []
        
        agent_config = {
            "role": "Ecommerce Site Navigation and Pagination Specialist",
            "goal": """
            Navigate ecommerce websites efficiently and prepare pages for data extraction.
            Handle all site-specific challenges including popups, dynamic content, and pagination
            without extracting any product data - focus purely on navigation and page preparation.
            """,
            "backstory": """
            You are a specialized web navigation expert with deep knowledge of UK retail platforms
            and their specific navigation patterns. Your sole responsibility is to navigate websites,
            dismiss blocking elements, handle dynamic content loading, and manage pagination.
            
            Your core expertise includes:
            - Multi-vendor popup handling (cookie consent, age verification, newsletters, location selection)
            - Dynamic content loading (infinite scroll, "Load More" buttons, lazy loading)
            - Pagination detection and navigation (next/previous buttons, page numbers, infinite scroll)
            - Site-specific navigation patterns for UK retailers (ASDA, Tesco, Waitrose, etc.)
            - Page preparation and verification for extraction readiness
            - Error recovery and alternative navigation strategies
            - Respectful navigation with appropriate delays and rate limiting
            
            CRITICAL: You NEVER extract product data - your job is purely navigation and page preparation.
            Once a page is ready, you signal completion and let the ExtractionAgent handle data extraction.
            """,
            "verbose": verbose,
            "allow_delegation": False,
            "tools": tools,
            "max_iter": 4,
            "memory": settings.enable_crew_memory
        }

        if llm:
            agent_config["llm"] = llm

        self.agent = Agent(**agent_config)

    def get_agent(self) -> Agent:
        """Get the CrewAI agent instance."""
        return self.agent

    def create_navigation_task(self, vendor: str, category_url: str, page_number: int = 1, **kwargs):
        """Alias for create_page_navigation_task to match Flow calling pattern."""
        # Extract category from URL or use a default
        category = kwargs.get('category', 'products')
        return self.create_page_navigation_task(
            vendor=vendor,
            category=category,
            category_url=category_url,
            page_number=page_number,
            session_id=kwargs.get('session_id')
        )

    def create_page_navigation_task(self, 
                                  vendor: str, 
                                  category: str, 
                                  category_url: str, 
                                  page_number: int = 1,
                                  session_id: str = None):
        """Create a task for navigating to a category page and preparing it for extraction."""
        from crewai import Task

        task_description = f"""
        Navigate to {category_url} and prepare the page for data extraction.

        CRITICAL: You MUST use the tool name "simplified_stagehand_tool" with the operation parameter.

        EXACT TOOL CALLING FORMAT:
        Tool: simplified_stagehand_tool
        Action Input: {{"operation": "navigate", "url": "{category_url}"}}

        Tool: simplified_stagehand_tool
        Action Input: {{"operation": "act", "action": "Click the Accept button"}}

        SIMPLE WORKFLOW:
        1. Call simplified_stagehand_tool with {{"operation": "navigate", "url": "{category_url}"}}
        2. Call simplified_stagehand_tool with {{"operation": "act", "action": "Click Accept cookies button"}}
        3. Return success status

        POPUP HANDLING:
        - Use simplified_stagehand_tool with {{"operation": "observe", "instruction": "Find cookie banner or modal dialog"}}
        - Use simplified_stagehand_tool with {{"operation": "act", "action": "Click I Accept button"}}
        - Ignore navigation links and footer elements

        SUCCESS CRITERIA:
        - Page loads successfully
        - Popups are dismissed
        - Products are visible
        - Page is ready for extraction

        REMEMBER: Always use "simplified_stagehand_tool" as the tool name, never use "navigate", "act", "observe" as tool names.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Navigation status report containing:
            - status: "page_ready" | "error" | "no_products_found"
            - page_info: {{
                "current_page": {page_number},
                "products_visible": <number_of_product_elements_visible>,
                "page_url": "{category_url}",
                "popups_handled": <list_of_popups_dismissed>,
                "dynamic_content_loaded": <true/false>,
                "ready_for_extraction": <true/false>
              }}
            - message: "Detailed description of navigation actions taken"
            
            Example successful output:
            {{
              "status": "page_ready",
              "page_info": {{
                "current_page": {page_number},
                "products_visible": 24,
                "page_url": "{category_url}",
                "popups_handled": ["cookie_consent", "newsletter_popup"],
                "dynamic_content_loaded": true,
                "ready_for_extraction": true
              }},
              "message": "Successfully navigated to {vendor} {category} page {page_number}, dismissed 2 popups, loaded 24 products, page ready for extraction"
            }}
            """
        )

    def create_pagination_detection_task(self, 
                                       vendor: str, 
                                       category: str, 
                                       current_page: int = 1,
                                       session_id: str = None):
        """Create a task for detecting and handling pagination."""
        from crewai import Task

        task_description = f"""
        Detect pagination options and navigate to the next page if available.
        
        Vendor: {vendor}
        Category: {category}
        Current Page: {current_page}
        Session ID: {session_id}

        PAGINATION DETECTION SEQUENCE:
        1. Scan the current page for pagination elements
        2. Identify pagination method (buttons, infinite scroll, load more)
        3. Determine if more pages/content are available
        4. If available, navigate to next page/load more content
        5. Prepare the new content for extraction

        PAGINATION METHODS TO CHECK:
        - "Next" or ">" buttons
        - Page number links (1, 2, 3, etc.)
        - "Load More" or "Show More" buttons
        - Infinite scroll detection
        - "View All" or "See More Products" links

        NAVIGATION ACTIONS:
        - If next page button exists: Click it and wait for page load
        - If "Load More" button exists: Click it and wait for new content
        - If infinite scroll: Scroll down to trigger more content loading
        - If no more pages: Return "no_more_pages" status

        CONTENT VERIFICATION:
        - Ensure new products have loaded after navigation
        - Verify page number has incremented (if applicable)
        - Check that new content is fully visible and ready
        - Handle any popups that appear after navigation

        CRITICAL: Focus only on pagination navigation, not product data extraction.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Pagination status report containing:
            - status: "next_page_ready" | "more_content_loaded" | "no_more_pages" | "error"
            - pagination_info: {{
                "previous_page": {current_page},
                "current_page": <new_page_number>,
                "pagination_method": "buttons" | "infinite_scroll" | "load_more" | "none",
                "has_more_pages": <true/false>,
                "new_products_loaded": <number_of_new_products>,
                "total_products_visible": <total_products_on_page>
              }}
            - message: "Description of pagination actions taken"
            
            Example outputs:
            - Next page available: {{"status": "next_page_ready", "pagination_info": {{"current_page": {current_page + 1}, "pagination_method": "buttons", "has_more_pages": true}}}}
            - No more pages: {{"status": "no_more_pages", "pagination_info": {{"current_page": {current_page}, "pagination_method": "buttons", "has_more_pages": false}}}}
            """
        )

    def create_infinite_scroll_handling_task(self, 
                                           vendor: str, 
                                           category: str,
                                           target_products: int = None,
                                           session_id: str = None):
        """Create a task for handling infinite scroll pagination."""
        from crewai import Task

        task_description = f"""
        Handle infinite scroll pagination to load all available products.
        
        Vendor: {vendor}
        Category: {category}
        Target Products: {target_products or "all available"}
        Session ID: {session_id}

        INFINITE SCROLL HANDLING:
        1. Count currently visible products
        2. Scroll down to trigger more content loading
        3. Wait for new products to load
        4. Repeat until no more products load or target reached
        5. Ensure all loaded content is fully visible

        SCROLL STRATEGY:
        - Scroll down in increments to trigger loading
        - Wait 3-5 seconds between scrolls for content to load
        - Monitor for new product elements appearing
        - Stop when no new products load after multiple attempts
        - Handle "Load More" buttons that may appear during scrolling

        CONTENT MONITORING:
        - Track total products loaded
        - Verify new products are fully rendered
        - Ensure images and details are loaded
        - Handle any loading indicators or spinners

        COMPLETION CRITERIA:
        - No new products load after 3 consecutive scroll attempts
        - Target product count reached (if specified)
        - "End of results" message appears
        - Maximum scroll limit reached for performance

        CRITICAL: Only handle scrolling and content loading, no data extraction.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Infinite scroll completion report:
            - status: "scroll_complete" | "target_reached" | "error"
            - scroll_info: {{
                "initial_products": <starting_product_count>,
                "final_products": <final_product_count>,
                "products_loaded": <new_products_loaded>,
                "scroll_attempts": <number_of_scrolls>,
                "completion_reason": "no_more_content" | "target_reached" | "max_scrolls"
              }}
            - message: "Description of infinite scroll handling"
            
            Example: {{"status": "scroll_complete", "scroll_info": {{"initial_products": 24, "final_products": 122, "products_loaded": 98, "completion_reason": "no_more_content"}}}}
            """
        )

    def create_popup_dismissal_task(self,
                                  vendor: str,
                                  popup_types: List[str] = None,
                                  session_id: str = None):
        """Create a task for comprehensive popup dismissal."""
        from crewai import Task

        popup_types = popup_types or ["cookie", "newsletter", "age", "location", "promotion", "app"]
        popup_list = ", ".join(popup_types)

        task_description = f"""
        Comprehensively handle and dismiss all blocking popups and overlays.

        Vendor: {vendor}
        Popup Types to Handle: {popup_list}
        Session ID: {session_id}

        POPUP DISMISSAL SEQUENCE:
        1. Scan page for any blocking elements or overlays
        2. Identify popup types based on content and appearance
        3. Apply appropriate dismissal strategy for each popup
        4. Verify main content is accessible after dismissal
        5. Handle any secondary popups that appear

        POPUP HANDLING STRATEGIES:
        {PopupHandler.get_popup_handling_instructions()}

        VENDOR-SPECIFIC HANDLING:
        {PopupHandler.get_vendor_specific_instructions(vendor)}

        VERIFICATION STEPS:
        - Confirm no overlays are blocking main content
        - Verify navigation elements are clickable
        - Check that product listings are visible
        - Ensure page is fully interactive

        CRITICAL: Be thorough but efficient - dismiss all blocking elements quickly.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Popup dismissal report:
            - status: "popups_dismissed" | "no_popups_found" | "partial_dismissal" | "error"
            - dismissal_info: {{
                "popups_found": <list_of_popup_types_detected>,
                "popups_dismissed": <list_of_successfully_dismissed_popups>,
                "dismissal_actions": <list_of_actions_taken>,
                "page_accessible": <true/false>,
                "remaining_issues": <list_of_unresolved_popups>
              }}
            - message: "Summary of popup dismissal actions"

            Example: {{"status": "popups_dismissed", "dismissal_info": {{"popups_found": ["cookie", "newsletter"], "popups_dismissed": ["cookie", "newsletter"], "page_accessible": true}}}}
            """
        )

    def create_page_verification_task(self,
                                    vendor: str,
                                    category: str,
                                    expected_elements: List[str] = None,
                                    session_id: str = None):
        """Create a task for verifying page readiness for extraction."""
        from crewai import Task

        expected_elements = expected_elements or ["product_listings", "navigation", "content"]

        task_description = f"""
        Verify that the page is fully loaded and ready for data extraction.

        Vendor: {vendor}
        Category: {category}
        Expected Elements: {", ".join(expected_elements)}
        Session ID: {session_id}

        VERIFICATION CHECKLIST:
        1. Main product listings are visible and loaded
        2. Product images are displayed (not loading placeholders)
        3. Product titles and prices are visible
        4. Navigation elements are accessible
        5. No loading spinners or "Loading..." messages
        6. No error messages or broken page elements
        7. Page content matches expected category

        ELEMENT VERIFICATION:
        - Product cards/tiles are fully rendered
        - Product information is complete and visible
        - Category navigation breadcrumbs are present
        - Pagination elements are accessible (if applicable)
        - Search and filter options are functional

        READINESS CRITERIA:
        - All critical page elements are loaded
        - No blocking overlays or popups remain
        - Content is stable (no ongoing loading)
        - Page is responsive to interactions

        CRITICAL: Ensure the page is completely ready before signaling extraction can begin.
        """

        return Task(
            description=task_description,
            agent=self.agent,
            expected_output=f"""
            Page verification report:
            - status: "page_ready" | "still_loading" | "error" | "no_content"
            - verification_info: {{
                "elements_verified": <list_of_verified_elements>,
                "missing_elements": <list_of_missing_expected_elements>,
                "loading_indicators": <list_of_active_loading_elements>,
                "page_errors": <list_of_error_messages_or_issues>,
                "extraction_ready": <true/false>
              }}
            - message: "Detailed page readiness assessment"

            Example ready: {{"status": "page_ready", "verification_info": {{"elements_verified": ["product_listings", "navigation"], "extraction_ready": true}}}}
            Example not ready: {{"status": "still_loading", "verification_info": {{"loading_indicators": ["product_spinner"], "extraction_ready": false}}}}
            """
        )
