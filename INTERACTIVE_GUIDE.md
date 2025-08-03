# 🤖 Interactive Ecommerce Scraper Guide

Welcome to the user-friendly interface for your CrewAI ecommerce scraping system! This guide will help you get started with the interactive features.

## 🚀 Quick Start

### Option 1: Dedicated Interactive Script (Recommended)
```bash
python interactive_scraper.py
```

### Option 2: Interactive Mode in Main Runner
```bash
python run_scraper.py interactive
# or simply
python run_scraper.py
```

## 🎯 What the Interactive Mode Does

The interactive scraper will guide you through:

1. **Environment Check** - Verifies your API keys and configuration
2. **Scraping Options** - Shows you available scraping modes
3. **User Input** - Asks for the sites/products you want to scrape
4. **Execution** - Runs your CrewAI agents to perform the scraping
5. **Results** - Shows you the extracted data and saves it to files

## 📋 Available Scraping Modes

### 1. Single Product Scraping 📦
- **What it does**: Scrapes detailed information from one product page
- **You'll be asked for**: Product URL
- **Best for**: Getting comprehensive data about a specific product
- **Example URLs**:
  - `https://demo.vercel.store/products/acme-mug`
  - `https://www.amazon.com/dp/[product-id]`
  - `https://www.ebay.com/itm/[item-id]`

### 2. Product Search & Scrape 🔍
- **What it does**: Searches for products on a site and scrapes multiple results
- **You'll be asked for**: 
  - Search query (e.g., "laptop", "coffee mug")
  - Target website URL
  - Number of products to scrape (1-20)
- **Best for**: Finding and comparing multiple products
- **Example sites**:
  - `https://demo.vercel.store`
  - `https://www.amazon.com`
  - `https://www.ebay.com`

### 3. Multiple URLs 📋
- **What it does**: Scrapes several specific product pages in batch
- **You'll be asked for**: List of product URLs (up to 10)
- **Best for**: Scraping a curated list of products
- **How it works**: Enter URLs one by one, press Enter with empty input to finish

### 4. Test System 🧪
- **What it does**: Runs system tests to verify everything is working
- **You'll be asked for**: Nothing - it runs automatically
- **Best for**: Troubleshooting and verification

## 🛠️ What Happens Behind the Scenes

When you run the interactive scraper, here's what your CrewAI system does:

1. **ProductScraperAgent** - Orchestrates the entire scraping process
2. **SiteNavigatorAgent** - Handles website navigation and search functionality
3. **DataExtractorAgent** - Uses AI to extract structured product data
4. **DataValidatorAgent** - Validates and cleans the extracted information

The agents work together using:
- **Stagehand** for browser automation
- **Browserbase** for cloud browser sessions
- **AI models** (GPT-4 or Claude) for intelligent extraction

## 📊 Output Files

The scraper saves results to JSON files:
- `single_product_result.json` - Single product scraping results
- `search_and_scrape_result.json` - Search operation results
- `multiple_products_result.json` - Batch scraping results
- `test_result.json` - System test results

## 🔧 Environment Requirements

Make sure your `.env` file contains:

```env
# Required
BROWSERBASE_API_KEY=your_browserbase_key
BROWSERBASE_PROJECT_ID=your_project_id

# At least one of these
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
```

## 💡 Tips for Best Results

1. **Start with the test mode** to verify everything works
2. **Use demo.vercel.store** for testing - it's reliable and fast
3. **Be specific with search queries** - "gaming laptop" vs "laptop"
4. **Respect rate limits** - don't scrape too many products at once
5. **Check the output files** for detailed extraction results

## 🚨 Troubleshooting

### "Missing Environment Variables" Error
- Check your `.env` file exists and has the required API keys
- Make sure you've copied the keys correctly (no extra spaces)

### "Import Error" Messages
- Run: `pip install -r requirements.txt`
- Make sure you're in the correct directory

### Scraping Fails
- Try the test mode first: `python interactive_scraper.py` → Option 4
- Check if the website is accessible in your browser
- Some sites may block automated access

### No Results Returned
- The site might have anti-bot protection
- Try with demo.vercel.store first to verify the system works
- Check the console output for error messages

## 🎉 Example Session

```
🤖 Welcome to the Interactive Ecommerce Scraper!
✅ Environment check passed!

🎯 Scraping Options
┌────────┬─────────────────────┬──────────────────────────────────────┐
│ Option │ Description         │ Best For                             │
├────────┼─────────────────────┼──────────────────────────────────────┤
│ 1      │ Single Product      │ Getting detailed info about one...   │
│ 2      │ Product Search      │ Finding and scraping products by...  │
│ 3      │ Multiple URLs       │ Scraping several specific product... │
│ 4      │ Test System         │ Verifying the scraper is working...  │
└────────┴─────────────────────┴──────────────────────────────────────┘

What would you like to do? [1]: 1

📦 Single Product Scraping
Enter the product URL you want to scrape [https://demo.vercel.store/products/acme-mug]: 

🚀 Scraping product: https://demo.vercel.store/products/acme-mug
✅ Product scraping completed!
📁 Results saved to: single_product_result.json

Would you like to perform another operation? [y/N]: n

🎉 Thank you for using the Interactive Ecommerce Scraper!
```

## 🔗 Next Steps

After using the interactive scraper:
1. Check the generated JSON files for your data
2. Try different scraping modes to see what works best
3. Experiment with different ecommerce sites
4. Consider integrating the results into your own applications

Happy scraping! 🛍️
