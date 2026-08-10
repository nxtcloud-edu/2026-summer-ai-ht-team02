export default function Ontology() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Enterprise Ontology</h1>
      <p className="text-gray-500 mb-4">
        기업 내부 데이터를 시설 — 공정 — 직무 — 스킬 — 물류 관계로 구조화합니다.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 시설 목록 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">시설 목록</h2>
          <p className="text-gray-400">등록된 시설이 없습니다.</p>
          {/* TODO: 시설 CRUD UI */}
        </div>

        {/* 온톨로지 그래프 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">관계 그래프</h2>
          <div className="h-64 flex items-center justify-center border-2 border-dashed border-gray-200 rounded">
            <p className="text-gray-400">시설을 선택하면 온톨로지 그래프가 표시됩니다.</p>
          </div>
          {/* TODO: NetworkX 데이터를 받아 D3/React Flow로 시각화 */}
        </div>
      </div>
    </div>
  )
}
