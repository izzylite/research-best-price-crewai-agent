"""Popup and banner handling utilities for ecommerce scraping."""

import time
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PopupHandler:
    """Utility class for handling common ecommerce website popups and banners."""
    
    # Common popup dismissal strategies
    POPUP_STRATEGIES = [
        {
            "name": "Cookie Consent",
            "keywords": ["cookie", "consent", "privacy", "gdpr", "data protection"],
            "actions": [
                "Click Accept All",
                "Click I Accept", 
                "Click Accept Cookies",
                "Click Continue",
                "Click Allow All",
                "Click OK"
            ]
        },
        {
            "name": "Newsletter Signup",
            "keywords": ["newsletter", "subscribe", "email", "offers", "updates"],
            "actions": [
                "Click Close button",
                "Click No Thanks",
                "Click Skip",
                "Click Maybe Later",
                "Click Continue Shopping",
                "Click X button in top right corner"
            ]
        },
        {
            "name": "Age Verification",
            "keywords": ["age", "18+", "verify", "confirm your age", "adult"],
            "actions": [
                "Click Yes",
                "Click I am 18+",
                "Click Continue",
                "Type 25 in age field"
            ]
        },
        {
            "name": "Location Selection",
            "keywords": ["location", "country", "delivery", "region", "where"],
            "actions": [
                "Select United Kingdom",
                "Select UK",
                "Click Continue",
                "Click Stay on UK site"
            ]
        },
        {
            "name": "Promotional Banners",
            "keywords": ["sale", "offer", "discount", "free delivery", "promotion"],
            "actions": [
                "Click Close",
                "Click Dismiss",
                "Click No Thanks",
                "Click Continue Shopping",
                "Click X button"
            ]
        },
        {
            "name": "Mobile App Prompts",
            "keywords": ["app", "download", "mobile", "get the app"],
            "actions": [
                "Click Continue in Browser",
                "Click Not Now",
                "Click Stay on Web",
                "Click No Thanks"
            ]
        }
    ]
    
    @staticmethod
    def get_popup_handling_instructions() -> str:
        """Get comprehensive popup handling instructions for agents."""
        return """
        CRITICAL POPUP HANDLING INSTRUCTIONS:
        
        1. IMMEDIATELY after page navigation, scan for blocking elements
        2. Handle popups in this order of priority:
           a) Cookie consent banners (highest priority)
           b) Privacy policy dialogs
           c) Newsletter signup popups
           d) Age verification prompts
           e) Location/country selection
           f) Promotional banners
           g) Mobile app download prompts
        
        3. For each popup type, try these actions:
           - Cookie consent: "Accept All", "I Accept", "Accept Cookies"
           - Privacy dialogs: "Accept", "I Agree", "Continue" (ONLY in modal dialogs, NOT footer links)
           - Newsletter: "Close", "No Thanks", "Skip", "X"
           - Age verification: "Yes", "I am 18+", enter "25"
           - Location: "United Kingdom", "UK", "Continue"
           - Promotions: "Close", "Dismiss", "No Thanks"
           - App prompts: "Continue in Browser", "Not Now"

        CRITICAL: DO NOT CLICK THESE ELEMENTS (they are navigation, not popups):
           - "Register", "Sign In", "Login", "Create Account", "Sign Up"
           - "Privacy Policy", "Terms", "Cookies" links in footer or navigation
           - Any links that will navigate away from the product page
           - Only click buttons/elements that DISMISS popups, not navigate to other pages
        
        4. VERIFY main content is accessible before proceeding
        5. If popups persist, try alternative dismiss strategies
        6. Wait 2-3 seconds between attempts
        7. CRITICAL: Check current URL - if on login.asda.com or similar, navigate back to product page
        8. AVOID footer elements - only interact with modal dialogs and overlay popups
        9. If no actual popups are found, proceed to next step (don't click random links)
        """
    
    @staticmethod
    def get_vendor_specific_instructions(vendor: str) -> str:
        """Get vendor-specific popup handling instructions."""
        vendor_instructions = {
            "asda": """
            ASDA-specific popup handling:
            - Look for privacy dialog with "Your privacy is important to us" text
            - Click "I Accept" button (not just "Accept")
            - Handle location prompts for delivery areas
            - Dismiss promotional banners for weekly offers
            """,
            "tesco": """
            TESCO-specific popup handling:
            - Cookie consent banner with "Accept All" button
            - Clubcard signup prompts - click "Not Now" or "Skip"
            - Age verification for alcohol - click "Yes" or enter age
            - Delivery location selection - choose UK postcode area
            """,
            "waitrose": """
            WAITROSE-specific popup handling:
            - Newsletter signup overlays - click "No Thanks"
            - Location-based delivery prompts - select area or skip
            - Cookie policy banners - click "Accept"
            - Partnership card prompts - dismiss if not needed
            """,
            "next": """
            NEXT-specific popup handling:
            - Newsletter subscription overlays - click "Close" or "X"
            - Size guide popups - dismiss if not needed
            - Cookie consent banners - click "Accept All"
            - Mobile app prompts - click "Continue in Browser"
            """,
            "primark": """
            PRIMARK-specific popup handling:
            - Cookie consent with "Accept" button
            - Newsletter popups - click "No Thanks"
            - Store locator prompts - dismiss if not needed
            - Promotional offer overlays - click "Close"
            """,
            "mamas_papas": """
            MAMAS & PAPAS-specific popup handling:
            - Newsletter signup - click "No Thanks" or "Skip"
            - Cookie consent - click "Accept All"
            - Age-appropriate product warnings - acknowledge
            - Delivery information popups - dismiss or continue
            """,
            "thetoyshop": """
            THE TOY SHOP-specific popup handling:
            - Age verification for toy safety - confirm appropriate age
            - Newsletter signup - click "Maybe Later"
            - Cookie consent - click "Accept"
            - Promotional toy offers - dismiss if not needed
            """,
            "costco": """
            COSTCO-specific popup handling:
            - Membership login prompts - click "Continue as Guest"
            - Location selection for warehouse - choose UK
            - Cookie consent - click "Accept All"
            - Bulk purchase notifications - acknowledge
            """
        }
        
        return vendor_instructions.get(vendor.lower(), "No specific instructions available for this vendor.")
    
    @staticmethod
    def create_popup_dismissal_command(popup_type: str) -> str:
        """Create a Stagehand command for dismissing a specific popup type."""
        commands = {
            "cookie": "Look for cookie consent banner or privacy dialog and click Accept All, I Accept, or Accept Cookies",
            "newsletter": "Look for newsletter signup popup and click Close, No Thanks, Skip, or X button",
            "age": "Look for age verification prompt and click Yes, I am 18+, or enter age 25",
            "location": "Look for location or country selection and choose United Kingdom or UK",
            "promotion": "Look for promotional banner or offer overlay and click Close, Dismiss, or No Thanks",
            "app": "Look for mobile app download prompt and click Continue in Browser or Not Now",
            "general": "Look for any popup, modal, or overlay blocking the main content and dismiss it appropriately"
        }
        
        return commands.get(popup_type, commands["general"])
    
    @staticmethod
    def get_verification_command() -> str:
        """Get command to verify popups have been dismissed."""
        return "Check if the main content is visible and accessible, with no overlays or popups blocking the page"


def handle_common_popups(stagehand_tool, vendor: str = None) -> List[str]:
    """
    Handle common popups using the provided Stagehand tool.
    
    Args:
        stagehand_tool: Instance of EcommerceStagehandTool
        vendor: Optional vendor name for specific handling
        
    Returns:
        List of actions taken
    """
    actions_taken = []
    
    try:
        # Wait for page to load
        time.sleep(3)
        
        # Handle cookie consent (highest priority)
        result = stagehand_tool._run(
            instruction=PopupHandler.create_popup_dismissal_command("cookie"),
            command_type="act"
        )
        if "completed" in result.lower():
            actions_taken.append("Dismissed cookie consent")
        
        # Handle newsletter popup
        result = stagehand_tool._run(
            instruction=PopupHandler.create_popup_dismissal_command("newsletter"),
            command_type="act"
        )
        if "completed" in result.lower():
            actions_taken.append("Dismissed newsletter popup")
        
        # Handle age verification
        result = stagehand_tool._run(
            instruction=PopupHandler.create_popup_dismissal_command("age"),
            command_type="act"
        )
        if "completed" in result.lower():
            actions_taken.append("Handled age verification")
        
        # Handle location selection
        result = stagehand_tool._run(
            instruction=PopupHandler.create_popup_dismissal_command("location"),
            command_type="act"
        )
        if "completed" in result.lower():
            actions_taken.append("Selected location/country")
        
        # Handle promotional banners
        result = stagehand_tool._run(
            instruction=PopupHandler.create_popup_dismissal_command("promotion"),
            command_type="act"
        )
        if "completed" in result.lower():
            actions_taken.append("Dismissed promotional banner")
        
        # Verify content is accessible
        verification = stagehand_tool._run(
            instruction=PopupHandler.get_verification_command(),
            command_type="observe"
        )
        
        logger.info(f"Popup handling completed. Actions taken: {actions_taken}")
        
    except Exception as e:
        logger.error(f"Error during popup handling: {str(e)}")
        actions_taken.append(f"Error: {str(e)}")
    
    return actions_taken
