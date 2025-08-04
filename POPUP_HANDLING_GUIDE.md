# 🚫 Popup and Banner Handling Guide

## Overview
This guide provides comprehensive instructions for handling blocking popups, banners, and dialogs that commonly appear on UK ecommerce websites. All agents using Stagehand tools MUST follow these procedures to ensure successful scraping.

## 🎯 Critical First Steps

**ALWAYS handle popups IMMEDIATELY after page navigation and BEFORE attempting any data extraction.**

### 1. Cookie Consent Banners
**Common Text:** "We use cookies", "Your privacy is important", "Cookie Policy"
**Actions to Try:**
- Click "Accept All"
- Click "I Accept" 
- Click "Accept Cookies"
- Click "Continue"
- Click "Allow All"
- Click "OK"

### 2. Privacy Policy Dialogs
**Common Text:** "Privacy Policy", "Data Protection", "Your privacy matters"
**Actions to Try:**
- Click "Accept"
- Click "I Agree"
- Click "Continue"
- Click "Proceed"
- Click "I Understand"

### 3. Newsletter Signup Popups
**Common Text:** "Subscribe", "Get offers", "Join our newsletter", "Stay updated"
**Actions to Try:**
- Click "Close" (X button)
- Click "No Thanks"
- Click "Skip"
- Click "Maybe Later"
- Click "Continue Shopping"
- Look for small X or close icon

### 4. Age Verification Prompts
**Common Text:** "Are you 18+?", "Age verification", "Confirm your age"
**Actions to Try:**
- Click "Yes"
- Click "I am 18+"
- Click "Continue"
- Enter age "25" or "30" in input field

### 5. Location/Country Selection
**Common Text:** "Choose your location", "Select country", "Where are you shopping?"
**Actions to Try:**
- Select "United Kingdom"
- Select "UK"
- Click "Continue"
- Click "Stay on UK site"

### 6. GDPR Compliance Banners
**Common Text:** "GDPR", "Data processing", "Manage preferences"
**Actions to Try:**
- Click "Accept"
- Click "Accept All"
- Click "Continue"
- Click "I Agree"

### 7. Promotional Banners/Offers
**Common Text:** "Special offer", "Sale", "Discount", "Free delivery"
**Actions to Try:**
- Click "Close"
- Click "Dismiss"
- Click "No Thanks"
- Click "Continue Shopping"
- Look for X or close button

### 8. Mobile App Download Prompts
**Common Text:** "Download our app", "Get the app", "Mobile app available"
**Actions to Try:**
- Click "Continue in Browser"
- Click "Not Now"
- Click "Stay on Web"
- Click "No Thanks"
- Click "Close"

## 🔍 Detection Strategies

### Visual Indicators
- Modal overlays covering content
- Semi-transparent backgrounds
- Centered dialog boxes
- Fixed position elements
- High z-index elements blocking content

### Common CSS Selectors to Look For
- `[class*="modal"]`
- `[class*="popup"]`
- `[class*="overlay"]`
- `[class*="banner"]`
- `[class*="consent"]`
- `[class*="cookie"]`
- `[class*="gdpr"]`
- `[id*="modal"]`
- `[id*="popup"]`

## 🛠️ Stagehand Implementation

### Step-by-Step Process
1. **Navigate to URL**
2. **Wait 2-3 seconds for page load**
3. **Scan for blocking elements**
4. **Attempt dismissal actions**
5. **Verify main content is accessible**
6. **Proceed with data extraction**

### Example Stagehand Commands
```python
# Check for and dismiss cookie banner
tool._run(
    instruction="Look for cookie consent banner and click Accept All or I Accept",
    command_type="act"
)

# Check for newsletter popup
tool._run(
    instruction="Look for newsletter signup popup and click Close or No Thanks",
    command_type="act"
)

# Verify content is accessible
tool._run(
    instruction="Check if the main product listing is visible and not blocked by overlays",
    command_type="observe"
)
```

## 🚨 Troubleshooting

### If Popups Persist
1. Try multiple dismiss strategies
2. Look for alternative close buttons
3. Check for nested popups
4. Wait longer for dynamic content
5. Try scrolling to trigger popup appearance

### Common Issues
- **Multiple popups:** Handle them sequentially
- **Delayed popups:** Wait and check again after 5 seconds
- **Persistent overlays:** Try pressing Escape key
- **Hidden close buttons:** Look for small X icons in corners

## 📋 Vendor-Specific Notes

### ASDA
- Privacy dialog with "I Accept" button
- Location selection for delivery areas
- Promotional banners for offers

### Tesco
- Cookie consent with "Accept All"
- Clubcard signup prompts
- Age verification for alcohol

### Waitrose
- Newsletter signup popups
- Location-based delivery prompts
- Cookie policy banners

### Next
- Newsletter subscription overlays
- Size guide popups
- Cookie consent banners

## ✅ Success Verification

After handling popups, verify:
- Main content is visible
- Product listings are accessible
- Navigation elements are clickable
- No overlay elements blocking interaction
- Page scrolling works normally

## 🔄 Integration with Agents

All agents should:
1. Include popup handling in their initial steps
2. Verify content accessibility before extraction
3. Report any persistent blocking elements
4. Use consistent dismissal strategies
5. Log successful popup handling for debugging

Remember: **Popup handling is CRITICAL for successful scraping. Never skip this step!**
