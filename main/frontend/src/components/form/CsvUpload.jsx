import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, FileText, X } from 'lucide-react'

export default function CsvUpload({ onFile, file, error }) {
  const onDrop = useCallback((accepted) => {
    if (accepted[0]) onFile(accepted[0])
  }, [onFile])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'], 'text/plain': ['.txt'] },
    maxFiles: 1,
  })

  return (
    <div>
      <div
        {...getRootProps()}
        className={`
          relative flex flex-col items-center justify-center gap-3 rounded-md
          border-2 border-dashed transition-colors duration-150 cursor-pointer
          min-h-[180px] p-6
          ${isDragActive
            ? 'border-sage-primary bg-sage-primary-container/30'
            : file
            ? 'border-sage-primary/50 bg-sage-surface-low'
            : error
            ? 'border-sage-error bg-sage-error-container/20'
            : 'border-sage-outline-var bg-sage-surface-low hover:border-sage-outline hover:bg-sage-surface-med'}
        `}
      >
        <input {...getInputProps()} />

        {file ? (
          <>
            <div className="w-12 h-12 rounded-full bg-sage-primary-container flex items-center justify-center">
              <FileText size={22} className="text-sage-on-primary-container" />
            </div>
            <div className="text-center">
              <p className="text-title-sm font-jakarta text-sage-on-surface">{file.name}</p>
              <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-0.5">
                {(file.size / 1024).toFixed(1)} KB · Click or drag to replace
              </p>
            </div>
          </>
        ) : (
          <>
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              error ? 'bg-sage-error-container' : 'bg-sage-surface-highest'
            }`}>
              <UploadCloud size={22} className={error ? 'text-sage-error' : 'text-sage-on-surface-var'} />
            </div>
            <div className="text-center">
              <p className="text-title-sm font-jakarta text-sage-on-surface">
                {isDragActive ? 'Drop your CSV here' : 'Drag & drop bank statement CSV'}
              </p>
              <p className="text-body-sm text-sage-on-surface-var font-jakarta mt-0.5">
                or <span className="text-sage-primary font-semibold">browse files</span> · .csv or .txt
              </p>
            </div>
            {error && (
              <p className="text-label-md text-sage-error font-jakarta">{error}</p>
            )}
          </>
        )}
      </div>

      {file && (
        <button
          onClick={(e) => { e.stopPropagation(); onFile(null) }}
          className="mt-2 flex items-center gap-1 text-label-md text-sage-on-surface-var hover:text-sage-error font-jakarta transition-colors"
        >
          <X size={13} /> Remove file
        </button>
      )}
    </div>
  )
}
