export default function RescuerView() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">구조대 현황</h1>

      {/* 미대피자 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-600">의식 불명 / 미대피</p>
          <p className="text-3xl font-bold text-red-700">—</p>
        </div>
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-sm text-yellow-600">SOS 요청</p>
          <p className="text-3xl font-bold text-yellow-700">—</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-sm text-green-600">대피 완료</p>
          <p className="text-3xl font-bold text-green-700">—</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 도면 위 미대피자 위치 */}
        <div className="bg-white rounded-lg shadow p-4 lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">미대피자 위치 (도면)</h2>
          <div className="h-96 flex items-center justify-center border-2 border-dashed border-gray-200 rounded">
            <p className="text-gray-400">도면 위 미대피자 마커 + 구조대 진입 경로</p>
            {/* TODO: 도면 + 미대피자 마커 + 진입 경로 표시 */}
          </div>
        </div>

        {/* 미대피자 목록 */}
        <div className="bg-white rounded-lg shadow p-4">
          <h2 className="text-lg font-semibold mb-4">대상자 목록</h2>
          <div className="space-y-3">
            <p className="text-gray-400 text-sm">미대피자가 없습니다.</p>
            {/* TODO: 미대피자 카드 (이름, 층, 위치, 심박, 마지막 업데이트) */}
          </div>

          <hr className="my-4" />

          <h3 className="font-semibold mb-2">활성 SOS</h3>
          <div className="space-y-2">
            <p className="text-gray-400 text-sm">활성 SOS가 없습니다.</p>
            {/* TODO: SOS 목록 (발신자, 위치, 시간) */}
          </div>
        </div>
      </div>
    </div>
  )
}
