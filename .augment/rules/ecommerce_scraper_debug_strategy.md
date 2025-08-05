---
type: "agent_requested"
description: "Example description"
---
# Ecommerce Scraper Debug Strategy Protocol

## MANDATORY DEBUG STRATEGY FOR ALL ECOMMERCE SCRAPER ISSUES

This comprehensive debug strategy must be followed for all ecommerce scraper troubleshooting tasks. This protocol has proven highly effective for identifying and resolving complex multi-agent scraping issues.

---

## **Phase 1: Problem Identification & Analysis**

### 1.1 Precise Problem Definition
- **Identify the specific failing component**:
  - Navigation Agent (popup handling, page preparation)
  - Extraction Agent (data extraction, schema compliance)
  - Validation Agent (data validation, error handling)
  - Stagehand Tool (browser automation, API calls)
  - CrewAI Flow (agent orchestration, task management)

### 1.2 Symptom Documentation
- **Capture exact error messages** with full stack traces
- **Document expected vs actual behavior** with specific examples
- **Include relevant log excerpts** from terminal output
- **Note any patterns** in failure modes or timing
- **Identify data quality issues** (fake vs real data, missing fields, etc.)

### 1.3 Context Gathering
- **Review recent changes** to agent configurations or instructions
- **Check API key status** and service availability
- **Verify website accessibility** and structure changes
- **Examine session management** and resource cleanup

---

## **Phase 2: Direct Verification with Browserbase Tools**

### 2.1 Manual Website Testing
```bash
# Use Browserbase tools to replicate agent actions
browserbase_session_create_browserbase()
browserbase_stagehand_navigate_browserbase(url="target_url")
browserbase_stagehand_observe_browserbase(instruction="find_elements")
browserbase_stagehand_extract_browserbase(instruction="extract_data")
```

### 2.2 Step-by-Step Replication
- **Navigate to the exact URL** the agent is trying to access
- **Handle popups manually** using the same approach as the agent
- **Test extraction commands** with identical instructions
- **Verify data availability** and structure on the target page
- **Document what works** and what fails at each step

### 2.3 Data Validation
- **Confirm real data exists** on the target page
- **Test different extraction approaches** (schema-based vs observe-then-act)
- **Validate data completeness** against expected schema
- **Check for dynamic content loading** or infinite scroll requirements

---

## **Phase 3: Agent Simulation & Instruction Optimization**

### 3.1 Instruction Testing
- **Execute exact agent instructions** using Browserbase tools
- **Test instruction variations** to find optimal formats
- **Validate schema-based extraction** with proper JSON output
- **Identify working selector patterns** and element targeting

### 3.2 Best Practice Implementation
- **Follow Stagehand best practices**:
  - Use schema-based extraction over observe-then-act when possible
  - Implement proper variable substitution for sensitive data
  - Use built-in DOM settling instead of manual waits
  - Apply observe-then-act only for complex interactions

### 3.3 Instruction Refinement
- **Document working instruction formats** for each agent type
- **Create reusable instruction templates** for common scenarios
- **Test edge cases** and error conditions
- **Validate instruction consistency** across different vendors/categories

### 3.4 Official MCP Pattern Implementation
**CRITICAL**: Always follow official Browserbase MCP patterns for optimal results:

**Extract Tool Pattern** (Simplified API):
```python
# Official pattern - Direct API call
result = tool._run(
    operation="extract",
    instruction="Extract all products with names, prices, weights. Return JSON array."
)
```

**Act Tool Pattern** (Atomic Actions):
```python
# Official pattern - Atomic actions only
result = tool._run(
    operation="act",
    action="Click the accept cookies button",
    variables={"sensitive_data": "value"}  # For sensitive data only
)
```

**Key Principles from Official Implementation**:
- ✅ **Direct API calls**: Use `stagehand.page.extract(instruction)` directly
- ✅ **Instruction-based**: Natural language instructions, not complex selectors
- ✅ **Universal approach**: No vendor-specific logic needed
- ✅ **Simple error handling**: Clean try/catch with descriptive messages
- ✅ **JSON serialization**: Proper handling of Pydantic models and objects
- ❌ **Avoid abstractions**: No command_type or complex parameter systems
- ❌ **Avoid vendor logic**: No site-specific selectors or special cases

---

## **Phase 4: Research & Documentation Review**

### 4.1 Official Documentation Research
**CrewAI Documentation**: https://docs.crewai.com/en/introduction
- Agent behavior and task instruction best practices
- Tool usage patterns and error handling
- Multi-agent orchestration and communication
- Flow architecture and state management

**Stagehand Documentation**: https://docs.stagehand.dev/get_started/introduction
- Schema-based extraction methods and patterns
- Observe-then-act workflow implementation
- Variable substitution and security practices
- Error handling and retry mechanisms

**Official Browserbase MCP Repository**: https://github.com/browserbase/mcp-server-browserbase
- **CRITICAL**: Study official MCP tool patterns for best practices
- Direct API usage: `stagehand.page.extract(instruction)` and `stagehand.page.act({action, variables})`
- Simple instruction-based approach without complex abstractions
- Proper session management with context sharing
- Clean error handling and JSON serialization
- Universal patterns that work across all sites (no vendor-specific logic)

**Scrappey Documentation**: https://docs.scrappey.com/docs/welcome
- AI-powered data extraction with anti-bot bypass
- Structured extraction with CSS selectors and schemas
- Browser emulation and session management
- Proxy rotation and CAPTCHA solving
- API request formats and response handling

### 4.2 Research Tool Usage
```python
research_task-master-ai(
    query="specific_issue_description with context",
    detailLevel="high",
    projectRoot="G:/lastAttempt"
)
```

### 4.3 Cross-Reference Validation
- **Compare research findings** with Browserbase test results
- **Identify discrepancies** between documentation and implementation
- **Document version compatibility** issues
- **Note deprecated methods** or updated best practices

---

## **Phase 5: Implementation & Comprehensive Validation**

### 5.1 Solution Implementation
- **Apply fixes incrementally** based on research and testing
- **Update agent instructions** with validated formats
- **Implement proper error handling** and retry logic
- **Add comprehensive logging** for debugging future issues

### 5.2 End-to-End Testing
- **Test complete scraper workflow** from start to finish
- **Validate multiple vendor/category combinations**
- **Check data quality and schema compliance**
- **Verify resource cleanup** and session management

### 5.3 Stability Validation
- **Run multiple test iterations** to ensure consistency
- **Test under different conditions** (network latency, page load times)
- **Validate error recovery** and graceful degradation
- **Document performance metrics** and success rates

---

## **CRITICAL SUCCESS CRITERIA**

### Mandatory Requirements
- ✅ **Each phase must be completed** before proceeding to the next
- ✅ **All Browserbase testing must show working results** before implementing agent changes
- ✅ **Research must include specific documentation references** and quotes
- ✅ **Final implementation must be validated** with actual scraper execution
- ✅ **All findings and solutions must be documented** for future reference

### Quality Gates
- **Phase 1**: Clear problem definition with specific symptoms
- **Phase 2**: Working Browserbase commands that replicate desired functionality
- **Phase 3**: Optimized instructions that work consistently in manual testing
- **Phase 4**: Research-backed solutions with official documentation support
- **Phase 5**: Validated end-to-end solution with comprehensive testing

### Documentation Requirements
- **Problem analysis** with root cause identification
- **Working instruction formats** for each agent type
- **Research findings** with documentation references
- **Implementation changes** with before/after comparisons
- **Test results** with success metrics and edge case handling

---

## **Phase 6: Official MCP Pattern Analysis (BREAKTHROUGH INSIGHTS)**

### 6.1 Key Discoveries from Official Repository Study
**Repository Location**: `mcp-server-browserbase-main/` (cloned for analysis)

**Critical Findings**:
- ✅ **Simplicity Wins**: Official tools are 50%+ simpler than custom implementations
- ✅ **Direct API Usage**: No abstraction layers or command_type systems
- ✅ **Universal Instructions**: Natural language works better than selectors
- ✅ **JSON Serialization**: Proper handling of complex objects with `default=str`
- ✅ **Session Management**: Context-based sharing with automatic cleanup

### 6.2 Proven Implementation Patterns
**SimplifiedStagehandTool Success**:
- 📊 **59-60 products extracted** from ASDA (vs previous failures)
- 📉 **52% code reduction** (640 → 306 lines)
- 🎯 **Universal approach** (no vendor-specific logic)
- ⚡ **Better performance** through direct API calls
- 🛠️ **Easier maintenance** following official patterns

### 6.3 Anti-Patterns to Avoid
Based on official repository analysis:
- ❌ **Complex command_type systems** - Use direct operations instead
- ❌ **Vendor-specific selectors** - Use universal instructions
- ❌ **Multiple abstraction layers** - Keep it simple and direct
- ❌ **Custom session management** - Follow official context patterns
- ❌ **Complex error handling** - Use clean try/catch with descriptive messages

### 6.4 Migration Strategy
When debugging complex tools:
1. **Study official patterns** in `mcp-server-browserbase-main/src/tools/`
2. **Create simplified version** following official API usage
3. **Test side-by-side** with current implementation
4. **Migrate incrementally** once simplified version proves superior
5. **Document improvements** for future reference

---

## **APPLY THIS STRATEGY TO ALL ECOMMERCE SCRAPER DEBUGGING TASKS**

This protocol ensures systematic, thorough debugging that addresses root causes rather than symptoms, leading to robust and maintainable solutions. The addition of official MCP pattern analysis has proven to be a breakthrough approach for achieving significant improvements in code quality and performance.
