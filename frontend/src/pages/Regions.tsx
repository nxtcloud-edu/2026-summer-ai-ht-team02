export default function Regions() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Regional Intelligence</h1>
      <p className="text-gray-500 mb-4">
        지역의 인력풀 · 교육 · 산업 · 교통 · 부지 데이터를 기업 요구조건과 매핑합니다.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 지역 목록 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold mb-4">후보 지역</h2>
          <p className="text-gray-400">등록된 지역이 없습니다.</p>
          {/* TODO: 지역 목록 + 추가 버튼 */}
        </div>

        {/* 지도 */}
        <div className="bg-white rounded-lg shadow p-6 lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">지역 지도</h2>
          <div className="h-80 flex items-center justify-center border-2 border-dashed border-gray-200 rounded">
            <p className="text-gray-400">Leaflet 지도 영역 (후보지 마커 표시)</p>
          </div>
          {/* TODO: Leaflet 지도 연동 */}
        </div>
      </div>

      {/* 상세 정보 */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-sm text-gray-500 mb-2">인력풀</h3>
          <p className="text-gray-400 text-sm">지역 선택 시 표시</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-sm text-gray-500 mb-2">교육기관</h3>
          <p className="text-gray-400 text-sm">지역 선택 시 표시</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-sm text-gray-500 mb-2">산업단지</h3>
          <p className="text-gray-400 text-sm">지역 선택 시 표시</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-sm text-gray-500 mb-2">인프라</h3>
          <p className="text-gray-400 text-sm">지역 선택 시 표시</p>
        </div>
      </div>
    </div>
  )
}
