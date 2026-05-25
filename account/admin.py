from django.contrib import admin
from .models import UserProfile

@admin.action(description="Setujui/Verifikasi warga yang terpilih")
def verifikasi_warga_massal(modeladmin, request, queryset):
    """Aksi cepat untuk menyetujui banyak warga sekaligus via checkbox admin"""
    queryset.update(is_verified=True)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    # 1. Kolom yang akan muncul di halaman tabel utama Django Admin
    list_display = ('nama_lengkap', 'get_email', 'no_hp', 'role', 'is_verified')
    
    # 2. Membuat field 'is_verified' bisa langsung dicentang/diedit dari tabel utama (SUPER CEPAT)
    list_editable = ('is_verified',)
    
    # 3. Fitur filter di sebelah kanan untuk menyaring data berdasarkan role & status verifikasi
    list_filter = ('role', 'is_verified')
    
    # 4. Kolom pencarian untuk mempermudah mencari nama atau nomor HP warga
    search_fields = ('nama_lengkap', 'no_hp', 'user__email')
    
    # 5. Mendaftarkan tombol aksi massal yang dibuat di atas
    actions = [verifikasi_warga_massal]

    def get_email(self, obj):
        """Mengambil data email dari relasi model User"""
        return obj.user.email
    get_email.short_description = 'Email' # Mengubah judul kolom tabel menjadi 'Email'
