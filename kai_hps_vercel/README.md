# KAI HPS Price Intelligence · Vercel

Versi web demo berbahasa Indonesia. Lima halaman mencakup Dasbor, Analisis HPS, Eksplorasi Harga, Basis Referensi, dan Admin. Metode median, persentil, IQR, indeks, regresi linear, dan rekomendasi mengikuti prototipe Python. Versi web menggunakan pustaka standar untuk perhitungan dan openpyxl untuk Excel agar paket Vercel tetap ringan.

## Mencoba demo

Buka **Analisis HPS → Riwayat dan ekspor**, pilih **DEMO-HPS-001**, lalu klik **Unduh laporan Excel**. Untuk membuat analisis sendiri, isi nama analisis dan klik **Cari harga referensi**. Ubah keputusan bukti dan isi alasan untuk setiap pengecualian. Klik **Hitung benchmark**, lalu **Simpan analisis**.

Mode dasar memakai 67 observasi sintetis. Entri baru disimpan pada browser yang dipakai. Unduh laporan untuk membuat salinan yang bisa dipindahkan ke perangkat lain. Batas unggah prototipe web adalah 3 MB dan 250 baris per impor.

## Menjalankan lokal

Siapkan Node.js 22 dan Python 3.12. Buka terminal di folder proyek ini.

Terminal pertama:

```powershell
cd backend
python -m pip install -r requirements.txt
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Terminal kedua:

```powershell
cd frontend
npm ci
$env:HPS_LOCAL_API = "http://127.0.0.1:8000"
npm run dev
```

Buka [aplikasi lokal](http://localhost:3000). Pada Linux/macOS, gunakan `export HPS_LOCAL_API=http://127.0.0.1:8000` sebelum `npm run dev`.

## Memasang di Vercel

1. Ekstrak arsip, lalu unggah isi folder `kai_hps_vercel` ke repositori baru. Biarkan `vercel.json` berada di akar proyek.
2. Buka **Vercel → Add New → Project**, pilih repositori, lalu deploy. Vercel Services membangun `frontend/` sebagai Next.js dan `backend/` sebagai FastAPI dalam satu proyek. Jika dashboard meminta preset, pilih **Services**.
3. Uji halaman awal, `/api/health`, unggah bukti sintetis, dan unduh laporan dari Riwayat.

Dari terminal, jalankan `npx vercel@latest login` dan `npx vercel@latest deploy` di akar proyek untuk deploy pratinjau. Akun tanpa login dapat mencoba `npx vercel@latest deploy --temporary` dengan output tautan klaim sesuai aturan Vercel.

## Penyimpanan bersama untuk demo terbatas

Jika membutuhkan penyimpanan server, aktifkan perlindungan akses pada deployment dan hubungkan basis PostgreSQL kosong khusus demo. Tambahkan **HPS_DATABASE_URL** di pengaturan environment Vercel dengan koneksi PostgreSQL yang mengaktifkan TLS, lalu deploy ulang. API membuat skema dan mengisi data demo satu kali. Mode ini memberi penyimpanan bersama pada pengguna yang dapat mengakses deployment.

Gunakan data sintetis pada versi ini. Untuk penggunaan internal PT KAI, siapkan SSO, otorisasi tiap peran, audit beridentitas, dan persetujuan infrastruktur sebelum mengunggah data pengadaan asli.

## Struktur

- `frontend/app/` memuat antarmuka, formulir, grafik, dan penyimpanan browser untuk mode demo.
- `backend/main.py` memuat API pencarian, perhitungan, unggah, simpan, dan ekspor.
- `backend/engine/`, `backend/database/`, dan `backend/export/` memuat analitik, repositori PostgreSQL, dan laporan.
- `backend/test_api.py` menguji API. Pasang `httpx`, lalu jalankan `python -m unittest -v` dari `backend/`.
- `vercel.json` mengatur pembagian rute antara antarmuka dan API.

Panduan resmi [Next.js dan FastAPI di Vercel](https://vercel.com/templates/fast-api/next-js-fastapi-starter) dan [PostgreSQL di Vercel](https://vercel.com/docs/postgres).
