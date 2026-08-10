export default function Dashboard() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Site Planning Dashboard</h1>

      {/* 요약 카드 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">등록 시설</p>
          <p className="text-2xl font-bold">—</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">후보 지역</p>
          <p className="text-2xl font-bold">—</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">평가 완료</p>
          <p className="text-2xl font-bold">—</p>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <p className="text-sm text-gray-500">기획안 생성</p>
          <p className="text-2xl font-bold">—</p>
        </div>
      </div>

      {/* 최근 활동 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">최근 활동</h2>
        <p className="text-gray-400">아직 활동 내역이 없습니다.</p>
      </div>
    </div>
  )
}
