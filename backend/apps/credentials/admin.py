from django.contrib import admin

from .models import Credential, CredentialChunk, CredentialRecord

admin.site.register(Credential)
admin.site.register(CredentialRecord)
admin.site.register(CredentialChunk)
