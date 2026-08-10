export default function FloorPlan() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">도면 관리</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 층 선택 사이드바 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">층 목록</h2>
          <p className="text-gray-400 text-sm">건물을 선택하세요.</p>
          {/* TODO: 건물/층 목록 렌더링 */}
        </div>

        {/* 도면 뷰 */}
        <div className="bg-white rounded-lg shadow p-4 lg:col-span-3">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold">도면 뷰</h2>
            <div className="space-x-2">
              <button className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600">
                노드 추가
              </button>
              <button className="px-3 py-1 text-sm bg-gray-500 text-white rounded hover:bg-gray-600">
                엣지 연결
              </button>
            </div>
          </div>
          <div className="h-96 flex items-center justify-center border-2 border-dashed border-gray-200 rounded relative">
            <p className="text-gray-400">도면 이미지 + 노드/엣지 오버레이</p>
            {/* TODO: Canvas/SVG 도면 렌더링 + 그래프 편집 */}
          </div>

          {/* 범례 */}
          <div className="mt-4 flex gap-4 text-sm text-gray-600">
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-green-500 rounded-full inline-block"></span> 출구
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-blue-500 rounded-full inline-block"></span> 계단
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-gray-400 rounded-full inline-block"></span> 경로 노드
            </span>
            <span className="flex items-center gap-1">
              <span className="w-3 h-3 bg-red-500 rounded-full inline-block"></span> 화재 구역
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
