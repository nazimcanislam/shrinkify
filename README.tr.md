<div align="center">
  <img src="assets/icon.png" width="96" alt="Shrinkify ikonu" />
  <h1>Shrinkify</h1>
  <p>Medya dosyalarını analiz et, codec dönüşümü öner, kopyaları tespit et ve ayrıntılı bir HTML raporu oluştur.</p>

  ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
  ![ffmpeg](https://img.shields.io/badge/ffmpeg-gerekli-007808?logo=ffmpeg&logoColor=white)
  ![exiftool](https://img.shields.io/badge/exiftool-gerekli-4a90d9?logoColor=white)
  ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
  ![Lisans](https://img.shields.io/badge/lisans-MIT-blue)
  [![GitHub Sponsors](https://img.shields.io/github/sponsors/nazimcanislam?label=Sponsor&logo=GitHub)](https://github.com/sponsors/nazimcanislam)

  > **[Claude](https://claude.ai) (Anthropic) ile iş birliği içinde geliştirildi.** Bu proje, bir insan geliştirici ile Claude arasındaki iteratif bir konuşma aracılığıyla tasarlandı. Mimari, kod ve belgeler birlikte üretildi — gerçek bir insan–yapay zeka iş birliği.
</div>

---

## ✨ Özellikler

- 📊 **Akıllı Analiz** — ffprobe her dosya için codec, bit hızı, çözünürlük ve format bilgisini çıkarır
- 🔄 **Dönüştürme** — H.264 → H.265 (ffmpeg), JPEG → AVIF (ffmpeg + exiftool)
- 🎚️ **Kalite Profilleri** — Maksimum Küçültme / Dengeli / Koruyucu
- 📁 **Eksiksiz Çıktı** — dönüştürülmemiş dosyaları da kopyalar; çıktı klasörü tamamen bağımsız olur
- 🔁 **Kopya Tespiti** — hash tabanlı tespit ve silme
- 📄 **HTML Raporu** — tahmini tasarruf, codec dağılım grafikleri, dosya başına tablolar
- 🖥️ **CLI + GUI** — terminal ve tkinter masaüstü arayüzü
- 🔒 **Metadata Korunur** — tüm EXIF meta verileri (GPS, çekim tarihi, kamera modeli, yönelim) exiftool aracılığıyla eksiksiz kopyalanır
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

> **CPU mu, GPU mu — ne beklemeli:**
> Donanım encoder'ları çok daha hızlıdır ancak CPU (libx265) ile kıyaslandığında
> daha büyük çıktı dosyaları üretir. Testlerimizde 11.000 dosyanın (60 GB)
> GPU ile dönüştürülmesi yaklaşık 1–2 saat sürdü. Aynı işlem CPU ile çok daha
> uzun sürerdi. Maksimum sıkıştırma önceliğinizse CPU modunu tercih edin.
> Büyük koleksiyonları hızlıca işlemek ve yeterince iyi bir sıkıştırmayla
> yetinmek istiyorsanız GPU modu daha iyi bir seçimdir.

#### 🟥 AMD GPU Hızlandırma

AMD iGPU (Ryzen APU) kullanıcılarında `hevc_amf` encoder `ffmpeg` tarafından listelenebilir ancak driver kısıtlamaları nedeniyle çalışmayabilir. Shrinkify bu durumu otomatik algılar ve CPU tabanlı `libx265` encoding'e geçer. Harici AMD GPU'larda GPU acceleration genel olarak çalışır.

---

## 📋 Gereksinimler

- Python 3.10+
- ffmpeg + ffprobe (video ve görüntü dönüştürme, analiz için)
- exiftool (görüntü dönüştürmede metadata koruması için)

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

### exiftool kurulumu

exiftool, görüntü dönüştürme için zorunludur. Kurulu değilse, görüntü dönüştürme başlamadan önce engellenir — metadata kaybetmemek için ffmpeg hiç çalıştırılmaz.

**Windows (önerilen: WinGet)**

```powershell
winget install OliverBetz.ExifTool
```

Kurulumun ardından terminalinizi yeniden başlatın, ardından doğrulayın:

```powershell
exiftool -ver
```

**Windows (standalone — kurulum gerektirmez)**

1. [exiftool.org](https://exiftool.org) adresinden Windows Executable'ı indirin
2. `exiftool(-k).exe` dosyasını `exiftool.exe` olarak yeniden adlandırın
3. `gui.py`'nin yanına (proje kök dizinine) yerleştirin — Shrinkify otomatik olarak bulur

**macOS**

```bash
brew install exiftool
```

**Linux**

```bash
sudo apt install libimage-exiftool-perl   # Debian / Ubuntu
sudo dnf install perl-Image-ExifTool      # Fedora
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

| Profil | Video CRF | Görüntü CRF | Açıklama |
|---|---|---|---|
| `max` | 28 | 38 | En küçük dosyalar. Hafif kalite düşüşü, genellikle fark edilmez. |
| `balanced` | 24 | 27 | En iyi denge. Varsayılan olarak önerilir. |
| `conservative` | 20 | 18 | Minimum kalite kaybı. Daha büyük dosyalar, arşivleme için daha güvenli. |

---

## 📂 Çıktı Klasörü

Dönüştürülen dosyalar, taranan dizinin içindeki `shrinkified/` klasörüne gider ve **orijinal dosya adları korunur**. Orijinal dosyalar asla değiştirilmez.

```
C:\Takeout\
├── photo.jpg            ← orijinal, dokunulmadı
├── video.mp4            ← orijinal, dokunulmadı
└── shrinkified\
    ├── photo.avif       ← dönüştürüldü (AVIF, tüm metadata korundu)
    └── video.mp4        ← dönüştürüldü (H.265)
```

**"Orijinalleri kopyala"** etkinleştirildiğinde, dönüştürülmemiş dosyalar da `shrinkified/` içine kopyalanır; bu klasörü tamamen bağımsız bir yedek olarak kullanabilirsiniz.

---

## 🔄 Dönüştürme Kriterleri

| Kaynak | Hedef | Motor | Tahmini Tasarruf (dengeli) |
|---|---|---|---|
| H.264 (AVC) video | H.265 (HEVC) | ffmpeg | ~%55 |
| MPEG-4, MPEG-2 video | H.265 (HEVC) | ffmpeg | ~%55 |
| JPEG fotoğraf | AVIF | ffmpeg + exiftool | ~%30–40 |
| HEVC, AV1 video | — | — | Dokunulmaz |
| AVIF, HEIF fotoğraf | — | — | Dokunulmaz |
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
pyinstaller --onefile --windowed --icon=assets/icon.ico --name=Shrinkify gui.py
```

**macOS**
```bash
pyinstaller --onefile --windowed --icon=assets/icon.png --name=Shrinkify gui.py
```

**Linux**
```bash
pyinstaller --onefile --name=Shrinkify gui.py
```

Çalıştırılabilir dosya `dist/` klasöründe olacaktır.

> 📌 ffmpeg, ffprobe ve exiftool **pakete dahil edilmez** — kullanıcıların bunları ayrıca kurması gerekir. Tamamen bağımsız bir derleme için üç ikili dosyayı da `.exe`'nin yanına kopyalayın. Shrinkify, PATH'e başvurmadan önce çalıştırılabilir dosyanın bulunduğu dizini otomatik olarak arar.

---

## 🗂️ Proje Yapısı

```
shrinkify/
├── .github/workflows/
├── assets/
│   ├── icon.ico
│   └── icon.png
├── core/
│   ├── scanner.py      # ffprobe analizi + hash/kopya tespiti
│   ├── analyzer.py     # dönüştürme karar mantığı + kalite profilleri
│   ├── converter.py    # ffmpeg + exiftool dönüştürme pipeline'ı
│   ├── reporter.py     # HTML + terminal raporu
│   └── utils.py        # binary çözümleme, subprocess yardımcıları
├── docs/
│   └── index.html      # GitHub Pages kurulumu
├── cli.py              # Command-line interface
├── gui.py              # tkinter GUI
├── version.py
├── CHANGELOG.md
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🖼️ AVIF & HEVC Uyumluluğu

Tüm kütüphanenizi dönüştürmeden önce cihazlarınızın çıktı dosyalarını açıp açamadığını kontrol edin.

### İyi desteklenen ✅

| Platform | AVIF fotoğraflar | H.265 video |
|---|---|---|
| Windows 10 / 11 | ✅ yerel (Fotoğraflar uygulaması, Edge) | ✅ (ücretsiz [HEVC Video Uzantıları](https://apps.microsoft.com/detail/9nmzlz57r3t7) gerektirir) |
| macOS Ventura (13)+ | ✅ yerel | ✅ yerel |
| iOS 16+ | ✅ yerel | ✅ yerel |
| Android 10+ | ✅ yerel | ✅ çoğu cihaz |
| Modern tarayıcılar (Chrome, Firefox, Safari) | ✅ | ✅ |
| VLC (tüm platformlar) | ✅ | ✅ |

### Sorun yaşanabilecek durumlar ⚠️

| Platform | Notlar |
|---|---|
| Windows 7 / 8 / 8.1 | H.265 için yerel destek yok; AVIF modern bir görüntüleyici gerektirir |
| Android 9 ve öncesi | Tutarsız — üreticiye ve donanım dekoder'a bağlı |
| Eski Akıllı TV'ler (2018 öncesi) | Genellikle H.265 donanım dekoder'ı yok; AVIF desteği muhtemelen yok |
| Bazı eski dijital fotoğraf çerçeveleri | AVIF desteklenmez |

> 💡 AVIF telif ücreti olmayan, tüm modern büyük platformlarda yerel olarak desteklenen bir formattır. Dosyaları eski cihaz kullanan kişilerle paylaşıyorsanız, orijinalleri saklayın veya **Koruyucu** profilini kullanın. 2019 ve sonrası modern cihazlarda kişisel arşivleme için dönüştürme güvenlidir.

---

## 📄 Lisans

MIT

---

*Also available in: [🇬🇧 English](README.md)*
