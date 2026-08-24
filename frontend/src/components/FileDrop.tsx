import { useCallback, useState } from "react";
import { Upload, X, FileText } from "lucide-react";

interface FileDropProps {
  onFilesSelected?: (files: File[]) => void;
}

export default function FileDrop({ onFilesSelected }: FileDropProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const files = e.dataTransfer?.files;
      if (!files) return;
      const dropped: File[] = [];
      for (let i = 0; i < files.length; i++) {
        const f = files[i];
        if (f && /\.(csv|xlsx?|json|pdf)$/i.test(f.name)) {
          dropped.push(f);
        }
      }
      if (dropped.length > 0) {
        setFiles((prev: File[]) => [...prev, ...dropped]);
        onFilesSelected?.(dropped);
      }
    },
    [onFilesSelected],
  );

  const removeFile = (idx: number) => {
    setFiles((prev: File[]) => prev.filter((_, i) => i !== idx));
  };

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 p-4">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-md border-2 border-dashed p-6 transition-colors ${
          dragging
            ? "border-emerald-500 bg-emerald-500/10"
            : "border-slate-600 hover:border-slate-500"
        }`}
      >
        <Upload size={24} className="mb-2 text-slate-400" />
        <p className="text-sm text-slate-400">
          Drop CSV, Excel, JSON, or PDF files here
        </p>
        <p className="mt-1 text-xs text-slate-600">or click to browse</p>
      </div>

      {files.length > 0 && (
        <ul className="mt-3 space-y-1">
          {files.map((file, i) => (
            <li
              key={i}
              className="flex items-center justify-between rounded-md bg-slate-700/50 px-3 py-2"
            >
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-slate-400" />
                <span className="text-sm text-slate-300">{file.name}</span>
                <span className="text-xs text-slate-500">
                  {(file.size / 1024).toFixed(1)} KB
                </span>
              </div>
              <button
                onClick={() => removeFile(i)}
                className="text-slate-500 hover:text-slate-300"
              >
                <X size={14} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}