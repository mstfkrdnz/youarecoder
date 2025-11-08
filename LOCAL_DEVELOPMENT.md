# Local Development Workflow

Bu döküman YouAreCoder projesinin local development ve deployment workflow'unu açıklar.

## 🏗️ Workflow Prensibi

**Tüm development local ortamda yapılır, production'a sadece Git üzerinden deploy edilir.**

```
Local Development ──► Git Commit ──► Git Push ──► Deploy Script ──► Production
```

## 📂 Directory Structure

```
/home/mustafa/youarecoder/     # Local development directory
/root/youarecoder/              # Production server directory
```

## 🔧 Local Development

### 1. Yeni Feature Development

```bash
cd /home/mustafa/youarecoder

# Code değişikliklerini yap
# Test et (local ortamda)

# Git'e commit et
git add .
git commit -m "Feature açıklaması"
```

### 2. Testing Locally

```bash
# Virtual environment'ı aktif et
source venv/bin/activate

# Flask uygulamasını test et
FLASK_APP=app python -m flask run

# Ya da test suite'i çalıştır
python -m pytest tests/
```

## 🚀 Production Deployment

### Otomatik Deployment Script

```bash
cd /home/mustafa/youarecoder
./deploy.sh
```

**Deploy script şunları yapar:**

1. ✅ Git branch kontrolü (main branch'te olmalı)
2. ✅ Working directory temiz mi kontrol
3. ✅ Git remote'a push
4. ✅ Dosyaları production'a rsync ile sync
5. ✅ Database migration'ları çalıştır (varsa)
6. ✅ Production servisleri restart et
7. ✅ Health check yap

### Manuel Deployment (Gerekirse)

```bash
# 1. Git'e commit et
git add .
git commit -m "Changes description"
git push origin main

# 2. Production'a sync et
rsync -avz --delete \
    --exclude='.git/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='venv/' \
    /home/mustafa/youarecoder/ \
    root@37.27.21.167:/root/youarecoder/

# 3. Servisleri restart et
ssh root@37.27.21.167 "sudo systemctl restart youarecoder youarecoder-worker"
```

## 📋 Best Practices

### ✅ DO (Yapılması Gerekenler)

- ✅ Her feature için local'de test et
- ✅ Anlamlı commit mesajları yaz
- ✅ Production'a deploy etmeden önce Git'e commit et
- ✅ Deploy script'ini kullan (manuel sync yerine)
- ✅ Deploy sonrası application'ın çalıştığını kontrol et

### ❌ DON'T (Yapılmaması Gerekenler)

- ❌ Production server'da direkt kod değiştirme
- ❌ Git commit yapmadan deploy etme
- ❌ Working directory'de uncommitted changes varken deploy etme
- ❌ main branch'ten başka branch'i deploy etme

## 🔍 Troubleshooting

### Deployment Failed

```bash
# Service status kontrol et
ssh root@37.27.21.167 "systemctl status youarecoder"

# Log'ları kontrol et
ssh root@37.27.21.167 "tail -f /var/log/youarecoder/error.log"

# Manuel restart dene
ssh root@37.27.21.167 "sudo systemctl restart youarecoder youarecoder-worker"
```

### Git Conflicts

```bash
# Local değişiklikleri stash et
git stash

# Remote'tan pull et
git pull origin main

# Stash'i geri al
git stash pop

# Conflict'leri çöz ve commit et
git add .
git commit -m "Resolve conflicts"
```

### Uncommitted Changes

```bash
# Değişiklikleri commit et
git add .
git commit -m "Description"

# Ya da stash et
git stash

# Deploy et
./deploy.sh
```

## 🎯 Action-Based Template System

### Local Development

Action handler'ları geliştirmek için:

```bash
cd /home/mustafa/youarecoder/app/services/action_handlers/

# Yeni handler ekle
touch my_new_handler.py

# __init__.py'a export ekle
# action_executor.py'deki HANDLER_REGISTRY'e ekle

# Test et
python -m pytest tests/test_provisioner.py
```

### Deployment

```bash
# Local'de test et
pytest tests/test_provisioner.py -v

# Commit et
git add app/services/action_handlers/
git commit -m "Add new action handler"

# Deploy et
./deploy.sh
```

## 📊 Status Check Commands

```bash
# Production service status
ssh root@37.27.21.167 "systemctl status youarecoder youarecoder-worker"

# Active workspaces
ssh root@37.27.21.167 "sudo -u postgres psql -d youarecoder -c 'SELECT COUNT(*) FROM workspaces WHERE status='\''running'\'';'"

# Recent logs
ssh root@37.27.21.167 "tail -n 50 /var/log/youarecoder/error.log"

# Application URL test
curl -s https://youarecoder.com/ | grep "title"
```

## 🔐 Security Notes

- ✅ `.env` dosyaları asla Git'e commit edilmez (`.gitignore`'da)
- ✅ Credentials local'de tutulur, production'da environment variables olarak ayarlanır
- ✅ SSH key authentication kullanılır (password kullanılmaz)
- ✅ Deploy script sadece main branch'ten deploy eder

## 📚 Related Documentation

- [ACTION_BASED_TEMPLATE_SYSTEM_DESIGN.md](claudedocs/ACTION_BASED_TEMPLATE_SYSTEM_DESIGN.md) - Action-based system architecture
- [ACTION_BASED_SYSTEM_IMPLEMENTATION_PROGRESS.md](claudedocs/ACTION_BASED_SYSTEM_IMPLEMENTATION_PROGRESS.md) - Implementation progress
- [DEPLOYMENT.md](DEPLOYMENT.md) - Detailed deployment guide

---

**Last Updated**: 2025-11-08
**Workflow Status**: ✅ Active & Working
