# 🌙 RondaDigital: Sistem Informasi Keamanan Lingkungan Berbasis Web

Proyek Akhir Mata Kuliah Rekayasa Perangkat Lunak - **Kelompok 2 (Topik 06: Sistem Sosial)**.
Platform web responsif berkarakter Progressive Web App (PWA) untuk mendigitalisasi operasional siskamling tingkat RT melalui otomasi absensi, simulasi pemantauan, dan manajemen krisis darurat.

---

## 🛠️ Tech Stack & Ekosistem Sistem
* **Backend & DB:** Python, Django Framework v6, PostgreSQL (Supabase Cloud Database via Session Pooler Port 5432).
* **Cloud Media Storage:** Supabase Storage S3-Compatible Bucket (`media`) via `django-storages` (Untuk unggahan foto selfie absensi petugas).
* **Frontend & UI/UX:** HTML5, Tailwind CSS v4 (Standalone CLI `tailwindcss.exe`), Vanilla JavaScript (AJAX Polling).
* **UI Style Guide:** Terinspirasi dari tema **Samagov** (Aplikasi Pemkot Samarinda) dengan ciri khas **Bottom Navigation Bar** & adaptasi tema malam hari (*Cyber Siskamling Dark Theme*).

---

## 📁 Struktur Aplikasi (Django Apps) & Pembagian Kerja
Proyek ini dipecah menjadi **4 Aplikasi Utama** secara modular guna menghindari konflik saat *merge* data pada Git:

### 1. `accounts/` (Manajemen Identitas & Otorisasi)
* **Fungsi Utama:** Mengelola registrasi mandiri warga, login akun, profile, dan menyimpan field status otorisasi (`status_warga`: *Pending/Terverifikasi*).
* **Tanggung Jawab:** Manajemen verifikasi data warga oleh Ketua RT berada di bawah domain app ini.
* *📌 PIC Logic:* **Julian** & **Irfan**.

### 2. `patrol/` (Operasional Ronda & Siskamling Malam)
* **Fungsi Utama:** Mengatur tabel jadwal shift ronda mingguan, modul **Absensi Geotagging** (mengambil koordinat GPS browser + jepretan foto Webcam lokal), serta halaman **Simulasi CCTV** pos ronda (memutar berkas video lokal `.mp4` loop dengan teks timestamp dinamis berjalan).
* *📌 PIC Frontend & JS Integration:* **Kholis** & **Alfito**.

### 3. `emergency/` (Sistem Tanggap Darurat Kilat)
* **Fungsi Utama:** Mengelola fungsi **Smart Panic Button**. Menyediakan API endpoint khusus untuk dilacak oleh skrip JavaScript di sisi klien menggunakan **AJAX Polling berdurasi interval 3 detik**. Menangani pemicu sirine suara bahaya (`siren.mp3`) massal dan rekapitulasi data insiden lingkungan.
* *📌 PIC Logic & API:* **Irfan**.

### 4. `dashboard_rt/` (Panel Kontrol Ketua RT)
* **Fungsi Utama:** Panel eksklusif Ketua RT untuk memantau kondisi lingkungan secara makro tanpa masuk ke Django Admin bawaan pengembang. Berisi rangkuman data analitik, grafik rekap laporan insiden lingkungan bulanan, validasi verifikasi instan akun warga baru, serta kendali modifikasi jadwal siskamling.
* *📌 PIC Layout & Integration:* **Irfan** & **Siswan**.

---

## 🔄 Alur Logika & Batasan Sistem (SOP Operasional)

### 🔓 1. Alur Pendaftaran & Penguncian Fitur (Otorisasi)
* Warga melakukan registrasi mandiri di aplikasi. Saat akun pertama kali dibuat, sistem secara default menetapkan `status_warga = Pending`.
* **Kondisi Akun Pending:** Warga sudah bisa masuk ke aplikasi, melihat jadwal ronda, dan membaca pengumuman, **TETAPI** fitur utama **Smart Panic Button** pada Bottom Navbar berstatus *Disabled* (Terkuci) dengan notifikasi "Menunggu Validasi Ketua RT".
* Ketua RT masuk ke `dashboard_rt`, memeriksa keaslian data warga baru tersebut, kemudian mengklik tombol "Setujui Warga". Status berubah menjadi `Terverifikasi`, dan seluruh fitur darurat otomatis terbuka penuh.

### 🕒 2. Alur Perubahan Antarmuka Otomatis (POV Switch)
Aplikasi menerapkan teknologi *Role-Adaptive Dynamic UI* yang mendeteksi peran user dan waktu sistem saat ini:
* **Mode Warga (Siang/Malam):** Hanya menampilkan antarmuka standar portal informasi lingkungan dan akses tombol Panic Button.
* **Mode Petugas Ronda (Malam Hari 22:00 - 05:00):** Jika pengguna login merupakan warga yang terjadwal bertugas ronda pada malam tersebut, saat jam menyentuh pukul 22:00, UI aplikasi secara dinamis akan memunculkan menu **"Absensi Shift"** (Akses Kamera + GPS) dan tab pemantauan **"Simulasi CCTV"**.

### 🚨 3. Alur Komunikasi Panic Button (AJAX Polling 3s)
* Sistem tidak menggunakan arsitektur WebSocket penuh, melainkan mengandalkan **AJAX Polling dengan interval 3 detik** guna menjaga efisiensi performa server.
* Setiap 3 detik, JavaScript di browser warga akan mengirimkan sinyal latar belakang (*background request*) ke endpoint `/emergency/api/status/`.
* Jika ada warga yang menekan tombol darurat, rekor bahaya masuk ke database. Pada hitungan polling berikutnya (maksimal 3 detik), seluruh browser warga lain yang sedang aktif membuka web akan menerima status bahaya tersebut, merubah layar menjadi merah berkedip, dan menyalakan audio sirine peringatan secara otomatis.

---

## 👥 Susunan Anggota Kelompok & Peran
1.  **Muhammad Irfan:** Lead Backend, System Architecture, & Database.
2.  **M. Rizky Julian Noor:** Backend Support & User Authentication Logic.
3.  **M. Nurkholis Hidayat:** Lead Frontend UI & JavaScript Integration.
4.  **Alfito Rayzha D:** Front End UI Assistant & JavaScript Integration.
5.  **Siswan Aryadi:** Technical Writer (SRS/UML Dokumentasi).