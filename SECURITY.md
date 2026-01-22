# Security Guide

## API Key Protection

This application has been hardened to prevent API key exposure. Here are the security measures in place:

### ✅ Implemented Protections

1. **No UI Display**
   - API keys are NEVER shown in the user interface
   - Keys are only loaded from environment variables or Streamlit secrets
   - Status indicators show whether keys are loaded (✓/✗) without revealing values

2. **Sanitized Error Messages**
   - All error messages automatically replace API keys with `***API_KEY***`
   - Stack traces are sanitized before logging
   - No full tracebacks printed that could expose sensitive data

3. **Git Protection**
   - `.env` file is in `.gitignore` (never committed)
   - `.streamlit/secrets.toml` is in `.gitignore`
   - Documentation uses placeholder values only

4. **Session State Security**
   - API keys stored in session state are never dumped or displayed
   - No debug functionality that could expose session state

5. **Server-Side Only**
   - All API calls are made server-side in Python
   - Keys never sent to client browser
   - No JavaScript access to keys

### 🔒 Best Practices

#### For Local Development:

1. **Use `.env` file** (automatically ignored by git)
   ```
   DEEPSEEK_API_KEY=your_key_here
   TAVILY_API_KEY=your_key_here
   SUPABASE_URL=your_url_here
   SUPABASE_KEY=your_key_here
   ```

2. **Never commit `.env` file**
   ```bash
   # Verify it's ignored:
   git status
   # Should NOT show .env in changes
   ```

3. **File permissions** (recommended):
   ```bash
   chmod 600 .env  # Owner read/write only
   ```

#### For Streamlit Cloud:

1. **Use Secrets Management**
   - Add keys in App Settings → Secrets
   - Never hardcode in code or documentation

2. **Rotate Keys If Exposed**
   - DeepSeek: https://platform.deepseek.com/api_keys
   - Tavily: https://app.tavily.com/
   - Supabase: Project Settings → API

3. **Monitor Usage**
   - Check API usage dashboards regularly
   - Set up usage alerts if available
   - Look for unexpected spikes

### ⚠️ What NOT To Do

❌ **NEVER** commit files with API keys:
- `.env`
- `.streamlit/secrets.toml`
- Any test files with hardcoded keys

❌ **NEVER** share screenshots showing:
- Streamlit secrets page
- Terminal output with keys visible
- Browser dev tools with session state

❌ **NEVER** log API keys:
- Don't use `print(api_key)`
- Don't include in error messages
- Don't put in debug output

### 🔍 Security Checklist

Before deploying or sharing code:

- [ ] `.env` file is in `.gitignore`
- [ ] No API keys in any committed files
- [ ] Documentation uses placeholders only
- [ ] Error handling sanitizes sensitive data
- [ ] No debug code that could expose keys
- [ ] Streamlit Cloud secrets are configured
- [ ] Local file permissions are restrictive

### 🚨 If Keys Are Exposed

If you accidentally commit API keys to GitHub:

1. **Immediately rotate all exposed keys**
   - Generate new keys in each service
   - Update `.env` and Streamlit Cloud secrets
   - Delete old keys from services

2. **Remove from Git history** (optional, advanced):
   ```bash
   # WARNING: This rewrites history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch path/to/file" \
     --prune-empty --tag-name-filter cat -- --all
   
   git push origin --force --all
   ```

3. **Monitor for unauthorized usage**
   - Check API usage dashboards
   - Look for unusual activity
   - Consider enabling 2FA where available

### 📞 Reporting Security Issues

If you discover a security vulnerability in this application, please:

1. **Do NOT** open a public GitHub issue
2. Contact the maintainer privately
3. Provide details about the vulnerability
4. Allow time for a fix before public disclosure

## Additional Resources

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [Streamlit Security Guidelines](https://docs.streamlit.io/knowledge-base/deploy/authentication-without-sso)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning/about-secret-scanning)
