---
type: "agent_requested"
description: "Example description"
---
# Official Browserbase MCP Server Analysis

## 📋 **Repository Information**

**Original Repository**: https://github.com/browserbase/mcp-server-browserbase  
**Cloned Date**: January 5, 2025  
**Purpose**: Reference for official MCP tool patterns and best practices  

## 🎯 **Key Insights Discovered**

### **Critical Patterns from Official Implementation:**

1. **Extract Tool** (`src/tools/extract.ts`):
   ```typescript
   // Direct API call - no abstractions
   const extraction = await stagehand.page.extract(params.instruction);
   return JSON.stringify(extraction, null, 2);
   ```

2. **Act Tool** (`src/tools/act.ts`):
   ```typescript
   // Atomic actions with variable substitution
   await stagehand.page.act({
     action: params.action,
     variables: params.variables,
   });
   ```

3. **Session Management** (`src/sessionManager.ts`):
   - Context-based session sharing
   - Automatic disconnect handling
   - Proper cleanup and resource management

### **Breakthrough Results Applied:**

**SimplifiedStagehandTool Success**:
- ✅ **59-60 products extracted** from ASDA
- ✅ **52% code reduction** (640 → 306 lines)
- ✅ **Universal approach** (no vendor-specific logic)
- ✅ **Better performance** through direct API calls

## 🔍 **Key Files to Study**

### **Core Tools:**
- `src/tools/extract.ts` - Data extraction patterns
- `src/tools/act.ts` - Action execution patterns  
- `src/tools/observe.ts` - Element observation patterns
- `src/tools/navigate.ts` - Navigation patterns

### **Infrastructure:**
- `src/context.ts` - Context management
- `src/sessionManager.ts` - Session lifecycle
- `src/stagehandStore.ts` - Stagehand instance management

### **Configuration:**
- `config.d.ts` - TypeScript configuration interfaces
- `package.json` - Dependencies and scripts

## 🚀 **Implementation Guidelines**

### **DO (Following Official Patterns):**
- ✅ Use direct `stagehand.page.extract(instruction)` calls
- ✅ Implement instruction-based API (natural language)
- ✅ Use simple error handling with descriptive messages
- ✅ Follow context-based session management
- ✅ Implement proper JSON serialization with `default=str`
- ✅ Use atomic actions for interactions

### **DON'T (Anti-Patterns):**
- ❌ Create complex command_type abstractions
- ❌ Implement vendor-specific selector logic
- ❌ Use multiple abstraction layers
- ❌ Create custom session management
- ❌ Overcomplicate error handling

## 📊 **Proven Benefits**

**Code Quality:**
- 52% reduction in code complexity
- Easier maintenance and debugging
- Better error messages and handling
- Industry-standard patterns

**Performance:**
- Direct API calls (no overhead)
- Universal instructions (no site-specific logic)
- Better extraction success rates
- Improved session stability

**Maintainability:**
- Following official patterns
- Clear separation of concerns
- Simple, readable code
- Comprehensive documentation

## 🎯 **Usage in Debug Strategy**

This reference should be consulted when:
1. **Debugging complex tool issues** - Compare with official patterns
2. **Creating new tools** - Follow official implementation patterns
3. **Optimizing existing tools** - Identify simplification opportunities
4. **Troubleshooting API issues** - Reference official API usage

## 📋 **Integration with Enhanced Debug Strategy**

This reference is now integrated into the enhanced debug strategy at:
`.augment/rules/ecommerce_scraper_debug_strategy.md`

**Phase 6: Official MCP Pattern Analysis** specifically references this directory for:
- Pattern analysis and comparison
- Implementation best practices
- Anti-pattern identification
- Migration strategies

## 🎉 **Success Story**

The study of these official patterns led to the creation of `SimplifiedStagehandTool`, which achieved:
- **60 products extracted** from ASDA (vs previous failures)
- **52% code reduction** while improving functionality
- **Universal approach** that works across all UK retail sites
- **Production-ready implementation** following industry best practices

This demonstrates the power of studying and following official patterns rather than creating complex custom implementations.

## 📁 **Directory Structure**

```
.augment/rules/official-mcp-reference/
├── ANALYSIS_README.md          # This analysis document
├── README.md                   # Original repository README
├── src/
│   ├── tools/                  # Core tool implementations
│   │   ├── extract.ts         # ⭐ Key extraction patterns
│   │   ├── act.ts             # ⭐ Key action patterns
│   │   ├── observe.ts         # Element observation
│   │   └── navigate.ts        # Navigation patterns
│   ├── context.ts             # ⭐ Context management
│   ├── sessionManager.ts      # ⭐ Session lifecycle
│   └── stagehandStore.ts      # Instance management
├── config.d.ts                # Configuration interfaces
└── package.json               # Dependencies and metadata
```

**⭐ = Critical files for pattern analysis**
