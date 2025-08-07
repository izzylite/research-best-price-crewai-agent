# Flexible Schema Usage Guide for SimplifiedStagehandTool

The `SimplifiedStagehandTool` now supports flexible, agent-defined extraction schemas instead of hardcoded ones. This allows agents to specify exactly what data they want to extract and in what format.

## 🎯 **Key Benefits**

- ✅ **Agent Flexibility:** Agents can define their own extraction schemas
- ✅ **Dynamic Schemas:** No need to modify tool code for different data structures
- ✅ **Backward Compatibility:** Still works with default schema if none provided
- ✅ **Type Safety:** Uses Pydantic for schema validation and type checking

## 📋 **Schema Definition Format**

Agents can provide custom schemas using this JSON format:

```json
{
  "fields": {
    "field_name": "field_type",
    "another_field": "field_type"
  },
  "name": "ModelName",
  "is_list": true/false
}
```

### **Supported Field Types:**
- `"str"` - Required string field
- `"optional_str"` - Optional string field (can be null)
- `"url"` - Required URL field (uses Pydantic HttpUrl for validation)
- `"optional_url"` - Optional URL field (can be null)
- `"int"` - Required integer field
- `"float"` - Required float field

### **Automatic URL Detection:**
Fields with names containing `url`, `link`, `image`, or `href` are automatically treated as URL fields even when using `str` or `optional_str` types.

## 🔧 **Usage Examples**

### **Example 1: Product Information Extraction**
```json
{
  "operation": "extract",
  "instruction": "Extract product information from this page",
  "schema": {
    "fields": {
      "name": "str",
      "price": "str",
      "image": "optional_url",
      "product_url": "optional_url",
      "description": "optional_str"
    },
    "name": "Product",
    "is_list": true
  }
}
```

### **Example 2: Contact Information Extraction**
```json
{
  "operation": "extract",
  "instruction": "Extract contact details from this page",
  "schema": {
    "fields": {
      "name": "str",
      "email": "optional_str",
      "phone": "optional_str",
      "address": "optional_str"
    },
    "name": "Contact",
    "is_list": false
  }
}
```

### **Example 3: Article Metadata Extraction**
```json
{
  "operation": "extract", 
  "instruction": "Extract article information",
  "schema": {
    "fields": {
      "title": "str",
      "author": "optional_str",
      "date": "optional_str",
      "content": "str"
    },
    "name": "Article",
    "is_list": false
  }
}
```

## 🤖 **Agent Implementation**

### **In Agent Task Descriptions:**
```python
task_description = f"""
Use simplified_stagehand_tool with custom schema for extraction:

Tool: simplified_stagehand_tool
Action Input: {{
  "operation": "extract",
  "instruction": "Extract product information",
  "schema": {{
    "fields": {{"name": "str", "price": "str", "image": "optional_str"}},
    "name": "Product", 
    "is_list": true
  }}
}}
"""
```

### **Expected Output Format:**
When `is_list: true`:
```json
[
  {
    "name": "Product Name",
    "price": "£19.99", 
    "image": "https://example.com/image.jpg"
  }
]
```

When `is_list: false`:
```json
{
  "name": "Product Name",
  "price": "£19.99",
  "image": "https://example.com/image.jpg"
}
```

## 🔄 **Fallback Behavior**

If no schema is provided, the tool uses a default product schema:
```python
class Product(BaseModel):
    name: str
    price: str
    url: Optional[str] = None
    image: Optional[str] = None
    description: Optional[str] = None
```

## ⚠️ **Best Practices**

1. **Keep schemas simple** - Use basic field types for better reliability
2. **Use optional fields** for data that might not always be present
3. **Set `is_list: true`** when extracting multiple items from a page
4. **Set `is_list: false`** when extracting single item or page metadata
5. **Provide clear instructions** that match your schema fields

## 🚀 **Advanced Usage**

### **Complex Extraction with Multiple Data Types and Proper URL Handling:**
```json
{
  "fields": {
    "product_name": "str",
    "current_price": "str",
    "original_price": "optional_str",
    "discount_percentage": "optional_str",
    "availability": "str",
    "rating": "optional_str",
    "review_count": "optional_str",
    "main_image": "optional_url",
    "thumbnail_images": "optional_url",
    "product_url": "url",
    "vendor_link": "optional_url"
  },
  "name": "DetailedProduct",
  "is_list": true
}
```

### **URL Field Examples:**
```json
{
  "fields": {
    "title": "str",
    "homepage": "url",
    "logo_image": "optional_url",
    "contact_link": "optional_url",
    "social_media_url": "optional_url"
  },
  "name": "WebsiteInfo",
  "is_list": false
}
```

## 🔗 **URL Validation Benefits**

Using `HttpUrl` type provides:
- ✅ **Automatic URL validation** - Invalid URLs are caught during extraction
- ✅ **Type safety** - Ensures extracted data is properly formatted URLs
- ✅ **Better error handling** - Clear error messages for malformed URLs
- ✅ **Stagehand compatibility** - Follows official Stagehand documentation patterns

This flexible schema system with proper URL handling allows agents to extract exactly the data they need in the correct format, making the tool much more versatile, reliable, and compliant with Stagehand best practices.
