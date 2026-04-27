from django.db import models
from django.conf import settings


class FileAttachment(models.Model):
    """Uploaded file attachment."""
    file = models.FileField(upload_to='attachments/%Y/%m/')
    original_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    file_type = models.CharField(max_length=50, blank=True, default='')
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_name} by {self.uploaded_by.username}"

    def get_file_url(self):
        if self.file:
            return self.file.url
        return None

    def is_image(self):
        return self.file_type.startswith('image/')

    def is_pdf(self):
        return self.file_type == 'application/pdf'

    def get_icon(self):
        if self.is_image():
            return 'image'
        elif self.is_pdf():
            return 'pdf'
        elif 'word' in self.file_type or 'document' in self.file_type:
            return 'doc'
        elif 'sheet' in self.file_type or 'excel' in self.file_type:
            return 'sheet'
        elif 'presentation' in self.file_type or 'powerpoint' in self.file_type:
            return 'ppt'
        return 'file'

    def get_size_display(self):
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"

    class Meta:
        ordering = ['-uploaded_at']
