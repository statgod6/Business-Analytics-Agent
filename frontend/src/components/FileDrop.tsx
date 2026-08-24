import { useCallback, useState } from "react";
import { Upload, X, FileText, Loader, Check } from "lucide-react";
import { uploadFile } from "../api/runs";

interface UploadingFile {
  file: File;
  progress: number;
  status: "pending" | "uploading" | "done" | "error";
  error?: string;
}

interface FileDropProps {
  runId?: string;
  onUploadComplete?: (files: { original_name: string; size: number }[]) => void;
}

export default function FileDrop({ runId, onUploadComplete }: FileDropProps) {
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [dragging, setDragging] = useState(false);

  const startUpload = useCallback(
    async (files: File[]) => {
      if (!runId) return;

      const newFiles: UploadingFile[] = files.map((f) => ({
        file: f,
        progress: 0,
        status: "pending" as const,
      }));
      setUploadingFiles((prev) => [...prev, ...newFiles]);

      const completed: { original_name: string; size: number }[] = [];

      for (const uf of newFiles) {
        setUploadingFiles((prev) =>
          prev.map((x) =>
            x.file === uf.file ? { ...x, status: "uploading" as const } : x,
          ),
        );

        try {
          await uploadFile(runId, uf.file, (pct) => {
            setUploadingFiles((prev) =>
              prev.map((x) =>
                x.file === uf.file ? { ...x, progress: pct } : x,
              ),
            );
          });
          setUploadingFiles((prev) =>
            prev.map((x) =>
              x.file === uf.file ? { ...x, status: "done" as const, progress: 100 } : x,
            ),
          );
          completed.push({
            original_name: uf.file.name,
            size: uf.file.size,
          });
        } catch (err) {
          setUploadingFiles((prev) =>
            prev.map((x) =>
              x.file === uf.file
                ? {
                    ...x,
                    status: "error" as const,
                    error: err instanceof Error ? err.message : "Upload failed",
                  }
                : x,
            ),
          );
        }
      }

      if (completed.length > 0) {
        onUploadComplete?.(completed);
      }
    },
    [runId, onUploadComplete],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const dt = e.dataTransfer?.files;
      if (!dt) return;
      const dropped: File[] = [];
      for (let i = 0; i < dt.length; i++) {
        const f = dt[i];
        if (f && /\.(csv|xlsx?|json|pdf)$/i.test(f.name)) {
          dropped.push(f);
        }
      }
      if (dropped.length > 0) {
        startUpload(dropped);
      }
    },
    [startUpload],
  );

  const removeFile = (idx: number) => {
    setUploadingFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const statusIcon = (uf: UploadingFile) => {
    switch (uf.status) {
      case "uploading":
        return <Loader size={14} className="animate-spin text-sky-400" />;
      case "done":
        return <Check size={14} className="text-emerald-400" />;
      case "error":
        return <X size={14} className="text-rose-400" />;
      default:
        return <FileText size={14} className="text-slate-400" />;
    }
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

      {uploadingFiles.length > 0 && (
        <ul className="mt-3 space-y-1">
          {uploadingFiles.map((uf, i) => (
            <li
              key={i}
              className="rounded-md bg-slate-700/50 px-3 py-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {statusIcon(uf)}
                  <span className="text-sm text-slate-300">{uf.file.name}</span>
                  <span className="text-xs text-slate-500">
                    {(uf.file.size / 1024).toFixed(1)} KB
                  </span>
                </div>
                {uf.status !== "uploading" && (
                  <button
                    onClick={() => removeFile(i)}
                    className="text-slate-500 hover:text-slate-300"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
              {uf.status === "uploading" && (
                <div className="mt-1 h-1 w-full overflow-hidden rounded-full bg-slate-600">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all duration-300"
                    style={{ width: `${uf.progress}%` }}
                  />
                </div>
              )}
              {uf.error && (
                <p className="mt-1 text-xs text-rose-400">{uf.error}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}