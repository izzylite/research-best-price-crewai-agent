# CrewAI StagehandTool Bug Tracking

## 🐛 Known Issue: model_api_key Not Forwarded to Remote Sessions

### Issue Summary
The CrewAI StagehandTool has a critical bug where it fails to properly forward the `model_api_key` parameter to remote Browserbase sessions, causing extraction operations to fail with "OPENAI_API_KEY environment variable is missing" errors.

### Bug Details
- **Error Message**: `The OPENAI_API_KEY environment variable is missing or empty; either provide it, or instantiate the OpenAI client with an apiKey option`
- **Root Cause**: StagehandTool constructor accepts `model_api_key` but doesn't pass it to the remote Browserbase session
- **Impact**: Navigation works, but data extraction fails
- **Affected Operations**: `extract` and `observe` commands that require LLM processing

### Reproduction
```python
from crewai_tools import StagehandTool
from stagehand.schemas import AvailableModel

# This will fail on extraction operations
stagehand_tool = StagehandTool(
    api_key="your_browserbase_api_key",
    project_id="your_project_id",
    model_api_key="your_openai_api_key",  # ❌ This parameter is not forwarded properly
    model_name=AvailableModel.GPT_4O,
    headless=True
)

# Navigation works ✅
result = stagehand_tool.run(
    instruction="Navigate to example.com",
    url="https://example.com",
    command_type="act"
)

# Extraction fails ❌
result = stagehand_tool.run(
    instruction="Extract the page title",
    command_type="extract"
)
```

## 📋 Official Fix Status

### Pull Request #381
- **Title**: "Stagehand Tool: Pass model API key as arg directly"
- **URL**: https://github.com/crewAIInc/crewAI-tools/pull/381
- **Author**: Derek Meegan (Browserbase team member)
- **Status**: ❌ Closed (July 19, 2025)
- **Reason**: Implementation challenges, not merged

### Related Issues
- **PR #359**: Lucas Gomide (CrewAI team) mentioned having "a very similar fix"
- **User Reports**: @areibman reported encountering this bug during WandB hackathon

### Monitoring Checklist
- [ ] Check CrewAI-tools releases for StagehandTool fixes
- [ ] Monitor https://github.com/crewAIInc/crewAI-tools/releases
- [ ] Watch for new pull requests addressing this issue
- [ ] Test official StagehandTool after each CrewAI-tools update

## 🔧 Current Workaround

### Our Custom Implementation
We've implemented a custom `EcommerceStagehandTool` that properly handles the API key forwarding:

**File**: `ecommerce_scraper/tools/stagehand_tool.py`

**Key Features**:
- ✅ Proper async/await handling
- ✅ Direct Stagehand SDK usage (bypasses CrewAI bug)
- ✅ Correct API key management
- ✅ Session cleanup and error handling

### Usage
```python
from ecommerce_scraper.tools.stagehand_tool import EcommerceStagehandTool

# This works correctly ✅
tool = EcommerceStagehandTool(
    api_key="your_browserbase_api_key",
    project_id="your_project_id",
    model_api_key="your_openai_api_key"
)
```

## 🔍 How to Check for Official Fix

### 1. Version Check
```bash
pip show crewai-tools
```

### 2. Test Script
Create a test script to verify if the bug is fixed:

```python
# test_stagehand_fix.py
from crewai_tools import StagehandTool
from stagehand.schemas import AvailableModel
import os

def test_official_stagehand_fix():
    """Test if CrewAI StagehandTool bug is fixed."""
    try:
        with StagehandTool(
            api_key=os.getenv("BROWSERBASE_API_KEY"),
            project_id=os.getenv("BROWSERBASE_PROJECT_ID"),
            model_api_key=os.getenv("OPENAI_API_KEY"),
            model_name=AvailableModel.GPT_4O,
            headless=True
        ) as tool:
            # Test extraction (this should work if bug is fixed)
            result = tool.run(
                instruction="Extract the page title",
                url="https://demo.vercel.store",
                command_type="extract"
            )
            
            if "Error" not in str(result) and "OPENAI_API_KEY" not in str(result):
                print("✅ BUG APPEARS TO BE FIXED!")
                return True
            else:
                print("❌ Bug still exists")
                return False
                
    except Exception as e:
        print(f"❌ Bug still exists: {e}")
        return False

if __name__ == "__main__":
    test_official_stagehand_fix()
```

### 3. Migration Plan
When the official fix is released:

1. **Update Dependencies**:
   ```bash
   pip install --upgrade crewai-tools
   ```

2. **Test Official Tool**:
   ```bash
   python test_stagehand_fix.py
   ```

3. **Replace Custom Implementation**:
   - Update `main.py` to use official `StagehandTool`
   - Remove custom `EcommerceStagehandTool`
   - Update agent configurations

4. **Verify Functionality**:
   ```bash
   python run_scraper.py --url "https://demo.vercel.store/products/acme-mug"
   ```

## 📅 Last Updated
- **Date**: August 3, 2025
- **CrewAI-tools Version**: 0.59.0 (bug still present)
- **Next Check**: Check weekly for updates

## 🔗 Useful Links
- [CrewAI-tools Repository](https://github.com/crewAIInc/crewAI-tools)
- [CrewAI-tools Releases](https://github.com/crewAIInc/crewAI-tools/releases)
- [Stagehand Documentation](https://docs.stagehand.dev/integrations/crew-ai)
- [Bug Report PR #381](https://github.com/crewAIInc/crewAI-tools/pull/381)

---

**Note**: This bug affects production usage of CrewAI StagehandTool. Continue using our custom implementation until official fix is confirmed and tested.
