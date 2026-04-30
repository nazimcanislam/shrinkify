<div align="center">
  <img src="icon.png" width="96" alt="Shrinkify ikonu" />
  <h1>Shrinkify</h1>
  <p>Medya dosyalarını analiz et, codec dönüşümü öner, kopyaları tespit et ve ayrıntılı bir HTML raporu oluştur.</p>

  ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
  ![ffmpeg](https://img.shields.io/badge/ffmpeg-gerekli-007808?logo=ffmpeg&logoColor=white)
  ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
  ![Lisans](https://img.shields.io/badge/lisans-MIT-blue)

  > **[Claude](https://claude.ai) (Anthropic) ile iş birliği içinde geliştirildi.** Bu proje, bir insan geliştirici ile Claude arasındaki iteratif bir konuşma aracılığıyla tasarlandı. Mimari, kod ve belgeler birlikte üretildi — gerçek bir insan–yapay zeka iş birliği.
</div>

---

## ✨ Özellikler

- 📊 **Akıllı Analiz** — ffprobe her dosya için codec, bit hızı, çözünürlük ve format bilgisini çıkarır
- 🔄 **Dönüştürme** — H.264 → H.265 (ffmpeg), JPEG/PNG → HEIF (pillow-heif)
- 🎚️ **Kalite Profilleri** — Maksimum Küçültme / Dengeli / Koruyucu
- 📁 **Eksiksiz Çıktı** — dönüştürülmemiş dosyaları da kopyalar; çıktı klasörü tamamen bağımsız olur
- 🔁 **Kopya Tespiti** — hash tabanlı tespit ve silme
- 📄 **HTML Raporu** — tahmini tasarruf, codec dağılım grafikleri, dosya başına tablolar
- 🖥️ **CLI + GUI** — terminal ve tkinter masaüstü arayüzü
- 🔒 **Metadata Korunur** — dönüştürme sonrası EXIF ve video metadata'sı saklanır
- ⚠️ **Hata Dayanıklı** — taranamayan dosyalar loglanır ve atlanır

> 🎵 **Not:** Shrinkify yalnızca fotoğraf ve videolara odaklanır. Ses dosyaları (MP3, FLAC, AAC vb.) analiz edilmez veya dönüştürülmez — bu, daha iyi ayrı bir araçla ele alınacak bağımsız bir konudur.

---

## 🖥️ Platform Desteği

Shrinkify **Windows** üzerinde test edilmiştir. Python ve ffmpeg platformlar arası olduğundan **Linux** ve **macOS** üzerinde de çalışması beklenir, ancak bu doğrulanmamıştır. Katkılarınızı bekliyoruz.

---

## ⚡ GPU Hızlandırma

`--hw-accel` bayrağı, donanım hızlandırmalı video kodlamayı etkinleştirir. Shrinkify **GPU'nuzu otomatik olarak tespit eder** ve mevcut en iyi encoder'ı seçer:

| Donanım | Encoder |
|---|---|
| NVIDIA | NVENC (H.265) |
| Intel | Quick Sync (QSV) |
| AMD | AMF |
| Apple Silicon | VideoToolbox |

Uyumlu bir GPU bulunamazsa otomatik olarak CPU kodlamaya geri döner.

**GPU hızlandırma neden kullanılmalı?**

- ⏱️ **Çok daha hızlı kodlama** — GPU encoder'lar, büyük video kütüphaneleri için genellikle CPU'dan 5–10× daha hızlıdır
- 🔋 **Daha düşük güç tüketimi** — özel encoder donanımı, CPU'yu tam yükte çalıştırmaya kıyasla çok daha az enerji harcar; bu da pil ömrünü uzatır
- 🌡️ **Daha az ısı** — sistem daha serin kalır; özellikle dizüstü bilgisayarlarda fark edilir
- 🖥️ **Sistem tepkili kalır** — GPU kodlamayı üstlenirken CPU başka görevler için serbest kalır

Tek dezavantajı, yavaş CPU profillerine kıyasla sıkıştırma verimliliğinin hafifçe düşmesidir. Ancak çoğu kullanım senaryosunda hız ve güç tasarrufu buna değer.

---

## 📋 Gereksinimler

- Python 3.10+
- ffmpeg + ffprobe (video dönüştürme ve analiz için)
- pillow + pillow-heif (görüntü dönüştürme için)

### Python bağımlılıklarını yükle

```bash
pip install pillow pillow-heif
```

### ffmpeg kurulumu

**Windows (önerilen: WinGet)**

```powershell
winget install Gyan.FFmpeg
```

Kurulumun ardından PATH güncellemesinin geçerli olması için **terminalinizi yeniden başlatın**, ardından doğrulayın:

```powershell
ffprobe -version
```

> ⚠️ **Sık karşılaşılan sorun:** ffmpeg kurulu olmasına rağmen Shrinkify bulunamıyor diyorsa, `bin` klasörü büyük ihtimalle sistem PATH'inde kayıtlı değildir. WinGet, ffmpeg'i şuna benzer bir konuma kurar:
> ```
> C:\Users\<KullanıcıAdınız>\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_...\ffmpeg-x.x-full_build\bin
> ```
> Bu `bin` klasörünü **Sistem Özellikleri → Ortam Değişkenleri → Path → Düzenle** yoluyla PATH'e manuel olarak ekleyin, ardından terminal ve uygulamayı yeniden başlatın.

**Windows (manuel)**

1. [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) adresinden `full_build` zip dosyasını indirin
2. Zipten çıkarın ve `bin` klasörünü sistem PATH'inize ekleyin
3. Doğrulama: terminal açın ve `ffprobe -version` komutunu çalıştırın

> ⚠️ Windows: Eğer `ffmpeg` bulunamazsa, **Shrinkify**'ı *Yönetici olarak* çalıştırmayı deneyin (sağ tıklayın → "Yönetici olarak çalıştır"). Bu, `ffmpeg` sistem genelinde yüklü olduğunda ancak PATH mevcut kullanıcı oturumunda kullanılamadığında gereklidir.

**macOS**

```bash
brew install ffmpeg
```

**Linux**

```bash
sudo apt install ffmpeg      # Debian / Ubuntu
sudo dnf install ffmpeg      # Fedora
```

---

## 🚀 Kullanım

### GUI

```bash
python gui.py
```

**İş Akışı:**

1. Bir klasör seçin
2. **Kalite profili** seçin (Dengeli önerilir)
3. İsterseniz **"Orijinalleri çıktı klasörüne kopyala"** seçeneğini etkinleştirin
4. **Analiz Et**'e tıklayın — dosyaları tarar, kopyaları tespit eder, HTML raporu oluşturur
5. **Dosyaları Dönüştür** veya **Kopyaları Sil** seçeneklerini bağımsız olarak kullanın
6. Hiçbir dosyayı değiştirmeden sonuçları önizlemek için **Kuru Çalıştır**'ı kullanın

### CLI

```bash
# Yalnızca analiz + HTML raporu
python cli.py "C:\Fotoğraflar"

# Analiz + dönüştürme (dengeli profil)
python cli.py "C:\Takeout" --convert

# Dönüştür + dönüştürülmemiş dosyaları da kopyala
python cli.py "C:\Takeout" --convert --copy-originals

# Maksimum sıkıştırma
python cli.py "C:\Takeout" --convert --preset max

# Kopyaları sil
python cli.py "C:\Medya" --duplicates

# Hiçbir dosyayı değiştirmeden her şeyi simüle et
python cli.py "C:\Medya" --convert --duplicates --dry-run

# GPU hızlandırmalı dönüştürme (NVIDIA / Intel / AMD / Apple Silicon otomatik tespit)
python cli.py "C:\Videolar" --convert --hw-accel
```

### CLI Seçenekleri

| Seçenek | Açıklama |
|---|---|
| `--convert` | Adayları dönüştür |
| `--preset <n>` | `max`, `balanced` (varsayılan) veya `conservative` |
| `--copy-originals` | Dönüştürülmemiş dosyaları da çıktı klasörüne kopyala |
| `--duplicates` | Kopya dosyaları sil |
| `--dry-run` | Simüle et — hiçbir dosya değiştirilmez veya silinmez |
| `--hw-accel` | GPU hızlandırmalı kodlama (donanımı otomatik tespit eder) |
| `--no-hash` | Hash hesaplamayı atla (daha hızlı, kopya tespiti olmadan) |
| `--report <dosya>` | HTML raporu dosya adı (varsayılan: shrinkify_report.html) |
| `--no-report` | HTML raporu oluşturmayı atla |

---

## 🎚️ Kalite Profilleri

| Profil | Video CRF | Görüntü Kalitesi | Açıklama |
|---|---|---|---|
| `max` | 28 | 60 | En küçük dosyalar. Hafif kalite düşüşü, genellikle fark edilmez. |
| `balanced` | 24 | 72 | En iyi denge. Varsayılan olarak önerilir. |
| `conservative` | 20 | 82 | Minimum kalite kaybı. Daha büyük dosyalar, arşivleme için daha güvenli. |

---

## 📂 Çıktı Klasörü

Dönüştürülen dosyalar, taranan dizinin içindeki `shrinkified/` klasörüne gider ve **orijinal dosya adları korunur**. Orijinal dosyalar asla değiştirilmez.

```
C:\Takeout\
├── photo.jpg            ← orijinal, dokunulmadı
├── video.mp4            ← orijinal, dokunulmadı
└── shrinkified\
    ├── photo.heic       ← dönüştürüldü
    └── video.mp4        ← dönüştürüldü (H.265)
```

**"Orijinalleri kopyala"** etkinleştirildiğinde, dönüştürülmemiş dosyalar da `shrinkified/` içine kopyalanır; bu klasörü tamamen bağımsız bir yedek olarak kullanabilirsiniz.

---

## 🔄 Dönüştürme Kriterleri

| Kaynak | Hedef | Motor | Tahmini Tasarruf (dengeli) |
|---|---|---|---|
| H.264 (AVC) video | H.265 (HEVC) | ffmpeg | ~%55 |
| MPEG-4, MPEG-2 video | H.265 (HEVC) | ffmpeg | ~%55 |
| JPEG fotoğraf | HEIF | pillow-heif | ~%30–40 |
| PNG fotoğraf | HEIF | pillow-heif | ~%30–40 |
| HEVC, AV1 video | — | — | Dokunulmaz |
| HEIF fotoğraf | — | — | Dokunulmaz |
| Düşük bit hızlı video (<3 Mbps) | — | — | Atlanır (zaten küçük) |

---

## 📦 Bağımsız Çalıştırılabilir Dağıtım

Python bağımlılığı olmadan tek dosyalık çalıştırılabilir oluşturmak için **PyInstaller** kullanın.

### PyInstaller kurulumu

```bash
pip install pyinstaller
```

### Derleme

**Windows**
```bash
pyinstaller --onefile --windowed --icon=icon.ico --name=Shrinkify gui.py
```

**macOS**
```bash
pyinstaller --onefile --windowed --icon=icon.png --name=Shrinkify gui.py
```

**Linux**
```bash
pyinstaller --onefile --name=Shrinkify gui.py
```

Çalıştırılabilir dosya `dist/` klasöründe olacaktır.

> 📌 `pillow` ve `pillow-heif` PyInstaller tarafından otomatik olarak paketlenir. ffmpeg/ffprobe **pakete dahil edilmez** — kullanıcıların bunları ayrıca kurması ve PATH'de bulunduğundan emin olması gerekir. Tamamen bağımsız bir derleme için ffmpeg ikili dosyalarını `.exe`'nin yanına kopyalayın ve `scanner.py` / `converter.py` içindeki PATH mantığını önce yerel dizini kontrol edecek şekilde güncelleyin.

---

## 🗂️ Proje Yapısı

```
shrinkify/
├── core/
│   ├── scanner.py      # ffprobe analizi + hash/kopya tespiti
│   ├── analyzer.py     # dönüştürme karar mantığı + kalite profilleri
│   ├── converter.py    # ffmpeg (video) + pillow-heif (görüntü) dönüştürme
│   └── reporter.py     # HTML + terminal raporu
├── cli.py              # Komut satırı arayüzü
├── gui.py              # tkinter GUI
├── icon.png            # Uygulama ikonu (512×512)
├── icon.ico            # Uygulama ikonu (Windows, çok boyutlu)
└── README.md
```

---

## 📺 HEIF & HEVC Uyumluluğu

Tüm kütüphanenizi dönüştürmeden önce cihazlarınızın çıktı dosyalarını açıp açamadığını kontrol edin.

### İyi desteklenen ✅

| Platform | HEIF fotoğraflar | H.265 video |
|---|---|---|
| Windows 10 / 11 | ✅ (ücretsiz [HEVC Video Uzantıları](https://apps.microsoft.com/detail/9nmzlz57r3t7) gerektirir) | ✅ aynı uzantı |
| macOS High Sierra (10.13)+ | ✅ yerel | ✅ yerel |
| iOS 11+ | ✅ yerel | ✅ yerel |
| Android 9+ | ✅ çoğu cihaz | ✅ çoğu cihaz |
| Modern Akıllı TV'ler (2018+) | ✅ çoğu | ✅ çoğu |
| VLC (tüm platformlar) | ✅ | ✅ |

### Sorun yaşanabilecek durumlar ⚠️

| Platform | Notlar |
|---|---|
| Windows 7 / 8 / 8.1 | Yerel HEIF veya H.265 desteği yok. VLC videoları oynatabilir. |
| Android 8 ve öncesi | Tutarsız — üreticiye ve donanım dekoder'a bağlı |
| Eski Akıllı TV'ler (2018 öncesi) | Genellikle H.265 donanım dekoder'ı yok |
| Bazı eski dijital fotoğraf çerçeveleri | HEIF desteklenmez |

> 💡 Dosyaları eski cihaz kullanan kişilerle paylaşıyorsanız, orijinalleri saklayın veya **Koruyucu** profilini kullanın. 2018 ve sonrası modern cihazlarda kişisel arşivleme için dönüştürme güvenlidir.

---

## 📄 Lisans

MIT

---

*Also available in: [🇬🇧 English](README.md)*
