def emergency_context(request):
    return {
        'kategori_list': [
            ('pencurian',    'Pencurian',          'Maling / Perampokan',    '⚠️'),
            ('kebakaran',    'Kebakaran',           'Kebakaran / Asap',       '🔥'),
            ('medis',        'Medis Darurat',       'Butuh Bantuan Medis',    '🫀'),
            ('mencurigakan', 'Orang Mencurigakan',  'Aktivitas Tidak Wajar',  '👁️'),
        ]
    }