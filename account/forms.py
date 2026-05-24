import re
from django import forms


class LoginForm(forms.Form):
    identifier = forms.CharField(
        error_messages={'required': 'Bidang ini wajib diisi.'}
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        error_messages={'required': 'Bidang ini wajib diisi.'}
    )


class RegisterForm(forms.Form):
    nama_lengkap = forms.CharField(
        max_length=100,
        error_messages={
            'required':  'Bidang ini wajib diisi.',
            'max_length': 'Nama lengkap terlalu panjang (maksimal 100 karakter).',
        }
    )
    email = forms.EmailField(
        error_messages={
            'required': 'Bidang ini wajib diisi.',
            'invalid':  'Format email tidak valid.',
        }
    )
    no_hp = forms.CharField(
        max_length=15,
        error_messages={
            'required':   'Bidang ini wajib diisi.',
            'max_length': 'Nomor telepon terlalu panjang (maksimal 15 digit).',
        }
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        error_messages={'required': 'Bidang ini wajib diisi.'}
    )

    # ── Validasi nama_lengkap ─────────────────────────────────────────────────
    def clean_nama_lengkap(self):
        nama = self.cleaned_data.get('nama_lengkap', '')

        if not nama.strip():
            raise forms.ValidationError('Nama lengkap tidak boleh hanya berisi spasi.')

        if not re.match(r'^[a-zA-Z\s]+$', nama):
            raise forms.ValidationError('Nama lengkap hanya boleh berisi huruf dan spasi.')

        return nama.strip()

    # ── Validasi email ────────────────────────────────────────────────────────
    def clean_email(self):
        email = self.cleaned_data.get('email', '')

        if ' ' in email:
            raise forms.ValidationError('Email tidak boleh mengandung spasi.')

        return email.lower()

    # ── Validasi no_hp ────────────────────────────────────────────────────────
    def clean_no_hp(self):
        no_hp = self.cleaned_data.get('no_hp', '').strip()

        if not no_hp.isdigit():
            raise forms.ValidationError('Nomor HP hanya boleh berupa angka.')

        if len(no_hp) < 10:
            raise forms.ValidationError('Nomor telepon terlalu pendek (minimal 10 digit).')

        if not (no_hp.startswith('08') or no_hp.startswith('62')):
            raise forms.ValidationError("Nomor HP harus diawali dengan '08' atau '62'.")

        return no_hp

    # ── Validasi password ─────────────────────────────────────────────────────
    def clean_password(self):
        password = self.cleaned_data.get('password', '')

        if len(password) < 8:
            raise forms.ValidationError('Password terlalu pendek (minimal 8 karakter).')

        if password.isdigit():
            raise forms.ValidationError('Password terlalu mudah. Gunakan kombinasi huruf dan angka.')

        return password