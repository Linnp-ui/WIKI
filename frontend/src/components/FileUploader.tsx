import React, { useState } from 'react';
import { cn } from '../lib/utils';

interface FileUploaderProps {
  onUploadSuccess?: () => void;
}

export function FileUploader({ onUploadSuccess }: FileUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFiles = async (files: FileList) => {
    const file = files[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const resp = await fetch('/api/system/ingest', {
        method: 'POST',
        body: formData,
      });
      if (!resp.ok) throw new Error(`Server ${resp.status}`);
      await resp.json();
      onUploadSuccess?.();
    } catch (e:any) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files);
    }
  };

  return (
    <div
      className={cn(
        'border-2 border-dashed rounded p-4 text-center cursor-pointer',
        dragActive ? 'border-theme-accent bg-theme-accent/10' : 'border-theme-border bg-theme-bg'
      )}
      onDragOver={e => { e.preventDefault(); setDragActive(true); }}
      onDragLeave={() => setDragActive(false)}
      onDrop={handleDrop}
      onClick={() => document.getElementById('file-input')?.click()}
    >
      {uploading ? (
        <p className="text-theme-accent">上传中...</p>
      ) : (
        <p className="text-theme-dim">拖放文件到此处或点击选择</p>
      )}
      <input
        id="file-input"
        type="file"
        className="hidden"
        accept=".pdf,.docx,.md,.txt"
        onChange={e => e.target.files && handleFiles(e.target.files)}
      />
      {error && <p className="mt-2 text-red-600">Error: {error}</p>}
    </div>
  );
}
