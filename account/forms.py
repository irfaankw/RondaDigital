import re
from django import forms
from django.core.exceptions import ValidationError
from .models import NIKWhitelist, UserProfile

# ── Validator reusable untuk file upload ──────────────────────
def validate_image_size(file):
    """Tolak file gambar lebih dari 5MB di level backend."""
    if hasattr(file, 'size') and file.size > 5 * 1024 * 1024:
        raise ValidationError('Ukuran file terlalu besar. Maksimal 5MB.')

class LoginForm(forms.Form):
    nik = forms.CharField(
        max_length=16,
        label='NIK',
        error_messages={'required': 'NIK wajib diisi.'}
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Password',
        error_messages={'required': 'Password wajib diisi.'}
    )

    def clean_nik(self):
        nik = self.cleaned_data.get('nik', '').strip()
        if not nik.isdigit():
            raise forms.ValidationError('NIK hanya boleh berupa angka.')
        if len(nik) != 16:
            raise forms.ValidationError('NIK harus terdiri dari 16 digit.')
        return nik

class RegisterForm(forms.Form):
    nik = forms.CharField(
        max_length=16,
        label='NIK',
        error_messages={'required': 'NIK wajib diisi.'}
    )
    nama_lengkap = forms.CharField(
        max_length=100,
        label='Nama Lengkap',
        error_messages={
            'required':   'Nama lengkap wajib diisi.',
            'max_length': 'Nama lengkap terlalu panjang.',
        }
    )
    no_hp = forms.CharField(
        max_length=15,
        label='Nomor HP',
        error_messages={'required': 'Nomor HP wajib diisi.'}
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Password',
        error_messages={'required': 'Password wajib diisi.'}
    )

    def clean_nik(self):
        nik = self.cleaned_data.get('nik', '').strip()
        if not nik.isdigit() or len(nik) != 16:
            raise forms.ValidationError('NIK harus 16 digit angka.')
        if not NIKWhitelist.objects.filter(nik=nik, is_used=False).exists():
            raise forms.ValidationError(
                'NIK kamu belum terdaftar di sistem RT, atau sudah digunakan. '
                'Hubungi RT untuk informasi lebih lanjut.'
            )
        return nik

    def clean_nama_lengkap(self):
        nama = self.cleaned_data.get('nama_lengkap', '').strip()
        nama = re.sub(r'\s+', ' ', nama)
        if not nama:
            raise forms.ValidationError('Nama lengkap tidak boleh kosong.')
        if not re.match(r'^[a-zA-Z\s]+$', nama):
            raise forms.ValidationError('Nama lengkap hanya boleh berisi huruf dan spasi.')
        return nama

    def clean_no_hp(self):
        no_hp = self.cleaned_data.get('no_hp', '').strip()
        if not no_hp.isdigit() or len(no_hp) < 10:
            raise forms.ValidationError('Nomor HP tidak valid (minimal 10 digit angka).')
        if not (no_hp.startswith('08') or no_hp.startswith('62')):
            raise forms.ValidationError("Nomor HP harus diawali '08' atau '62'.")
        if UserProfile.objects.filter(no_hp=no_hp).exists():
            raise forms.ValidationError('Nomor HP ini sudah digunakan oleh akun lain.')
        return no_hp

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8:
            raise forms.ValidationError('Password minimal 8 karakter.')
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Password wajib mengandung minimal 1 huruf besar.')
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Password wajib mengandung minimal 1 huruf kecil.')
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError('Password wajib mengandung minimal 1 angka.')
        return password

class ProfileForm(forms.ModelForm):
    """
    Form untuk melengkapi data identitas warga.
    RT dan RW tidak dimasukkan — sudah auto-terisi dari NIKWhitelist saat registrasi
    dan ditampilkan sebagai readonly di halaman profil.
    """
    tanggal_lahir = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='Tanggal Lahir',
        error_messages={'required': 'Tanggal lahir wajib diisi.'}
    )
    alamat = forms.CharField(
        required=True,
        label='Alamat Lengkap',
        error_messages={'required': 'Alamat wajib diisi.'}
    )
    pekerjaan = forms.CharField(
        required=True,
        label='Pekerjaan',
        error_messages={'required': 'Pekerjaan wajib diisi.'}
    )
    jenis_kelamin = forms.ChoiceField(
        required=True,
        choices=[('', '---------'), ('L', 'Laki-laki'), ('P', 'Perempuan')],
        label='Jenis Kelamin',
        error_messages={'required': 'Jenis kelamin wajib dipilih.'}
    )
    foto_ktp = forms.ImageField(
        required=False,
        validators=[validate_image_size],
        error_messages={'invalid_image': 'File bukan gambar yang valid.'}
    )
    foto_kk = forms.ImageField(
        required=False,
        validators=[validate_image_size],
        error_messages={'invalid_image': 'File bukan gambar yang valid.'}
    )

    class Meta:
        model  = UserProfile
        fields = [
            'alamat', 'tanggal_lahir', 'pekerjaan',
            'jenis_kelamin', 'foto_profil', 'foto_ktp', 'foto_kk',
        ]

    def clean(self):
        cleaned  = super().clean()
        foto_ktp = cleaned.get('foto_ktp')
        foto_kk  = cleaned.get('foto_kk')

        has_ktp = foto_ktp or (
            self.instance.pk and self.instance.foto_ktp and self.instance.foto_ktp.name
        )
        has_kk = foto_kk or (
            self.instance.pk and self.instance.foto_kk and self.instance.foto_kk.name
        )

        if not has_ktp and not has_kk:
            raise forms.ValidationError(
                'Upload minimal salah satu dokumen: Foto KTP atau Foto KK.'
            )
        return cleaned