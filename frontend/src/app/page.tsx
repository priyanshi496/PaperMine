import FileUpload from "@/components/FileUpload";

export default function Home() {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans">
      <main className="max-w-6xl mx-auto px-6 py-12">
        <header className="mb-12">
          <h1 className="text-4xl font-bold tracking-tight text-gray-900">PaperMine</h1>
          <p className="text-lg text-gray-600 mt-2">Intelligent Document Processing & Search</p>
        </header>

        <section className="mt-8">
          <FileUpload />
        </section>
      </main>
    </div>
  );
}
