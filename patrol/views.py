from django.shortcuts import render

def petugas_dashboard(request):
    # Mock data untuk ringkasan di halaman utama petugas
    context = {
        'user_profile': {'role': 'PETUGAS'},
        'total_laporan': 12,
        'status_ronda': 'Aman Kondusif',
    }
    return render(request, 'patrol/petugas_home.html', context)

def petugas_cctv(request):
    # Mock data daftar url/lokasi CCTV lingkungan RT
    context = {
        'user_profile': {'role': 'PETUGAS'},
        'cctv_list': [
            {'id': 1, 'lokasi': 'Gapura Utama RT 01', 'status': 'Online'},
            {'id': 2, 'lokasi': 'Pertigaan Pos Ronda', 'status': 'Online'},
            {'id': 3, 'lokasi': 'Area Lapangan Warga', 'status': 'Offline'},
        ]
    }
    return render(request, 'patrol/petugas_cctv.html', context)

def petugas_alert(request):
    # Mock data laporan darurat (seperti contoh yang kamu bagikan sebelumnya)
    context = {
        'user_profile': {'role': 'PETUGAS'},
        'laporan_list': [
            {
                'id': 1,
                'judul': 'Pencurian Motor',
                'pelapor': 'M. Nurkholis',
                'tanggal': '25 Mei 2026',
                'status': 'menunggu',  # oren
                'detail': 'Motor Scoopy hitam plat KT XXXX hilang di parkiran depan.'
            },
            {
                'id': 2,
                'judul': 'Kecelakaan Beruntun',
                'pelapor': 'Alfito Rayzha',
                'tanggal': '24 Mei 2026',
                'status': 'direspons',  # ungu
                'detail': 'Ada mobil nabrak tiang listrik dekat pos ronda.'
            },
            {
                'id': 3,
                'judul': 'Pencurian Helm',
                'pelapor': 'Siswan Aryadi',
                'tanggal': '20 Mei 2026',
                'status': 'selesai',  # hijau
                'detail': 'Helm KYT di atas motor hilang, tapi pelakunya sudah damai.'
            }
        ]
    }
    return render(request, 'patrol/alert.html', context)

def petugas_shift(request):
    # Mock data lengkap untuk absensi dan list jadwal shift malam ini
    shift_aktif_mock = {
        'waktu': '20:00 — 22:00',
        'nama_shift': 'Shift Pertama',
        'tanggal': 'Selasa, 2 Juni 2026'
    }

    jadwal_shift_list_mock = [
        {
            'inisial': 'BS',
            'nama': 'Budi Santoso',
            'waktu': '20:00 - 22:00',
            'status': 'Aktif',
            'bg_inisial': 'bg-cyan-500'
        },
        {
            'inisial': 'AF',
            'nama': 'Ahmad Fauzi',
            'waktu': '22:00 - 00:00',
            'status': 'Menunggu',
            'bg_inisial': 'bg-slate-700'
        },
        {
            'inisial': 'DK',
            'nama': 'Deni Kurniawan',
            'waktu': '00:00 - 02:00',
            'status': 'Menunggu',
            'bg_inisial': 'bg-slate-700'
        },
    ]

    context = {
        'user_profile': {'role': 'PETUGAS'},
        'shift_aktif': shift_aktif_mock,
        'jadwal_shift_list': jadwal_shift_list_mock,
    }
    return render(request, 'patrol/petugas_shift.html', context)