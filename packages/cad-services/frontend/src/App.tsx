import { useState, useEffect } from 'react'
import { Building2, Layers, LayoutGrid, Upload, Calculator } from 'lucide-react'

interface Project {
  id: number
  name: string
  description: string
  model_count: number
  created_at: string
}

interface Room {
  id: number
  number: string
  name: string
  area_m2: number
  floor_name: string
}

function App() {
  const [projects, setProjects] = useState<Project[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('projects')

  useEffect(() => {
    fetchProjects()
    fetchRooms()
  }, [])

  const fetchProjects = async () => {
    try {
      const res = await fetch('/api/v1/projects')
      const data = await res.json()
      setProjects(data.items || [])
    } catch (e) {
      console.error('Error fetching projects:', e)
    } finally {
      setLoading(false)
    }
  }

  const fetchRooms = async () => {
    try {
      const res = await fetch('/api/v1/rooms')
      const data = await res.json()
      setRooms(data.items || [])
    } catch (e) {
      console.error('Error fetching rooms:', e)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Building2 className="w-8 h-8 text-blue-600" />
              <h1 className="text-xl font-bold text-slate-900">CAD-Hub</h1>
            </div>
            <nav className="flex gap-4">
              <button
                onClick={() => setActiveTab('projects')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  activeTab === 'projects' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
                Projekte
              </button>
              <button
                onClick={() => setActiveTab('rooms')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  activeTab === 'rooms' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Layers className="w-4 h-4" />
                Räume
              </button>
              <button
                onClick={() => setActiveTab('upload')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  activeTab === 'upload' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Upload className="w-4 h-4" />
                Upload
              </button>
              <button
                onClick={() => setActiveTab('din277')}
                className={`px-4 py-2 rounded-lg flex items-center gap-2 ${
                  activeTab === 'din277' 
                    ? 'bg-blue-100 text-blue-700' 
                    : 'text-slate-600 hover:bg-slate-100'
                }`}
              >
                <Calculator className="w-4 h-4" />
                DIN 277
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
            <p className="mt-4 text-slate-600">Lade Daten...</p>
          </div>
        ) : (
          <>
            {activeTab === 'projects' && (
              <ProjectsView projects={projects} />
            )}
            {activeTab === 'rooms' && (
              <RoomsView rooms={rooms} />
            )}
            {activeTab === 'upload' && (
              <UploadView />
            )}
            {activeTab === 'din277' && (
              <DIN277View />
            )}
          </>
        )}
      </main>
    </div>
  )
}

function ProjectsView({ projects }: { projects: Project[] }) {
  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">Projekte</h2>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {projects.map((project) => (
          <div key={project.id} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 hover:shadow-md transition-shadow">
            <h3 className="font-semibold text-lg text-slate-900">{project.name}</h3>
            <p className="text-slate-600 mt-2 text-sm">{project.description}</p>
            <div className="mt-4 flex items-center gap-4 text-sm text-slate-500">
              <span>{project.model_count} Modelle</span>
            </div>
          </div>
        ))}
        {projects.length === 0 && (
          <p className="text-slate-500 col-span-3 text-center py-12">Keine Projekte gefunden</p>
        )}
      </div>
    </div>
  )
}

function RoomsView({ rooms }: { rooms: Room[] }) {
  const totalArea = rooms.reduce((sum, r) => sum + r.area_m2, 0)
  
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-slate-900">Räume</h2>
        <div className="bg-blue-50 text-blue-700 px-4 py-2 rounded-lg">
          Gesamtfläche: <strong>{totalArea.toFixed(2)} m²</strong>
        </div>
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nr.</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase">Etage</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 uppercase">Fläche</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {rooms.map((room) => (
              <tr key={room.id} className="hover:bg-slate-50">
                <td className="px-6 py-4 text-sm text-slate-900">{room.number}</td>
                <td className="px-6 py-4 text-sm text-slate-900">{room.name}</td>
                <td className="px-6 py-4 text-sm text-slate-600">{room.floor_name || '-'}</td>
                <td className="px-6 py-4 text-sm text-slate-900 text-right font-mono">{room.area_m2.toFixed(2)} m²</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function UploadView() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<string>('')

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      const res = await fetch('/api/v1/upload/ifc/1', {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      setResult(JSON.stringify(data, null, 2))
    } catch (e) {
      setResult('Upload fehlgeschlagen: ' + String(e))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">IFC Upload</h2>
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <div className="border-2 border-dashed border-slate-300 rounded-lg p-12 text-center">
          <Upload className="w-12 h-12 text-slate-400 mx-auto mb-4" />
          <input
            type="file"
            accept=".ifc,.ifczip"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="mb-4"
          />
          <p className="text-sm text-slate-500 mb-4">IFC oder IFCZIP Datei auswählen</p>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Hochladen'}
          </button>
        </div>
        {result && (
          <pre className="mt-6 bg-slate-900 text-green-400 p-4 rounded-lg text-sm overflow-x-auto">{result}</pre>
        )}
      </div>
    </div>
  )
}

function DIN277View() {
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const calculate = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/calculations/din277', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: 1 })
      })
      const data = await res.json()
      setResult(data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-slate-900 mb-6">DIN 277 Berechnung</h2>
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
        <button
          onClick={calculate}
          disabled={loading}
          className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 mb-6"
        >
          {loading ? 'Berechne...' : 'DIN 277 berechnen'}
        </button>
        
        {result && (
          <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-green-50 p-4 rounded-lg">
              <div className="text-sm text-green-600">NUF (Nutzfläche)</div>
              <div className="text-2xl font-bold text-green-700">{result.nuf_total} m²</div>
            </div>
            <div className="bg-yellow-50 p-4 rounded-lg">
              <div className="text-sm text-yellow-600">TF (Technik)</div>
              <div className="text-2xl font-bold text-yellow-700">{result.tf_total} m²</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-sm text-purple-600">VF (Verkehr)</div>
              <div className="text-2xl font-bold text-purple-700">{result.vf_total} m²</div>
            </div>
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-sm text-blue-600">NGF (Netto)</div>
              <div className="text-2xl font-bold text-blue-700">{result.ngf_total} m²</div>
            </div>
            <div className="bg-slate-100 p-4 rounded-lg">
              <div className="text-sm text-slate-600">BGF (Brutto)</div>
              <div className="text-2xl font-bold text-slate-700">{result.bgf_total} m²</div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
