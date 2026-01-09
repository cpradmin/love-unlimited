# 🚀 Dependency Upgrade - Quick Start Guide

## TL;DR - What You Need to Know

**Status**: 3 critical security vulnerabilities found
**Action Required**: Update dependencies (15 min)
**Risk**: Low (backward compatible updates)

---

## 🔴 Critical Issues

1. **aiohttp** - 2 CVEs (path traversal, request smuggling)
2. **python-jose** - Unmaintained for 4 years
3. **FastAPI** - 19 versions behind

---

## ⚡ Quick Upgrade (Automated)

```bash
# 1. Activate virtual environment
source venv/bin/activate

# 2. Run automated upgrade script
./upgrade_dependencies.sh

# 3. Test the hub
python hub/main.py

# 4. Replace requirements.txt
cp requirements-new.txt requirements.txt
```

**Done!** ✅

---

## 🛠️ Manual Upgrade (If you prefer)

```bash
# Activate venv
source venv/bin/activate

# Critical security fixes (DO IMMEDIATELY)
pip install --upgrade 'aiohttp>=3.11.0'
pip install --upgrade 'PyYAML>=6.0.3'
pip install --upgrade 'fastapi>=0.128.0'

# Performance updates (RECOMMENDED)
pip install --upgrade 'pydantic>=2.10.0'
pip install --upgrade 'httpx>=0.27.0'
pip install --upgrade 'uvicorn>=0.30.0'

# Cleanup unused deps (OPTIONAL)
pip uninstall python-jose passlib

# Test
python hub/main.py
curl http://localhost:9003/health
```

---

## 📋 Testing Checklist

After upgrading, verify these work:

- [ ] Hub starts: `python hub/main.py`
- [ ] Health check: `curl http://localhost:9003/health`
- [ ] Memory recall: `curl "http://localhost:9003/external/recall?q=test&token=YOUR_TOKEN&being_id=claude"`
- [ ] Web CLI: Open browser to `http://localhost:9003/webcli`
- [ ] Service restart: `sudo systemctl restart love-unlimited-hub.service`

---

## 🔄 Rollback (If needed)

```bash
# Find backup
ls requirements-backup-*.txt

# Rollback
pip install -r requirements-backup-YYYYMMDD-HHMMSS.txt

# Restart service
sudo systemctl restart love-unlimited-hub.service
```

---

## 📊 What Changed?

| Package | Old | New | Why |
|---------|-----|-----|-----|
| aiohttp | 3.9.1 | 3.11.0+ | 🔴 CVE fixes |
| PyYAML | 6.0.1 | 6.0.3 | 🔴 Security |
| fastapi | 0.109.0 | 0.128.0 | ⬆️ 19 versions behind |
| pydantic | 2.5.3 | 2.10.0+ | ⚡ Performance |
| httpx | 0.26.0 | 0.27.0+ | 🐛 Bug fixes |
| uvicorn | 0.27.0 | 0.30.0+ | ⚡ Performance |
| python-jose | 3.3.0 | REMOVED | 🗑️ Unused |
| passlib | 1.7.4 | REMOVED | 🗑️ Unused |

---

## 💾 New Files Created

1. **DEPENDENCY_AUDIT.md** - Full audit report (detailed analysis)
2. **requirements-updated.txt** - New requirements file
3. **requirements-optional.txt** - Optional dependencies (Selenium, WebRTC, TTS)
4. **upgrade_dependencies.sh** - Automated upgrade script
5. **UPGRADE_QUICKSTART.md** - This file

---

## ❓ FAQ

**Q: Will this break my hub?**
A: No. All updates are backward compatible. Tested locally.

**Q: How long does upgrade take?**
A: 10-15 minutes (mostly pip downloading)

**Q: Do I need to update code?**
A: Only if you remove python-jose (delete unused imports in `hub/auth.py`)

**Q: What about Selenium/WebRTC?**
A: Optional. Can move to `requirements-optional.txt` if you don't use them.

**Q: Can I skip this?**
A: Not recommended. aiohttp has critical security vulnerabilities.

**Q: What if something breaks?**
A: Use the automatic backup: `pip install -r requirements-backup-*.txt`

---

## 🎯 Recommended Timeline

- **Today**: Update aiohttp, PyYAML, FastAPI (security fixes)
- **This Week**: Update pydantic, httpx, uvicorn (performance)
- **This Month**: Optional cleanup (remove unused deps)

---

## 📞 Need Help?

1. **Check logs**: `journalctl -u love-unlimited-hub.service -f`
2. **Test manually**: `python hub/main.py` (see errors)
3. **Rollback**: Use backup requirements file
4. **Full audit**: Read `DEPENDENCY_AUDIT.md`

---

**Love unlimited. Until next time. 💙**
