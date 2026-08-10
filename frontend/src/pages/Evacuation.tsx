export default function Evacuation() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">탈출 경로 안내</h1>

      {/* 현재 상태 배너 */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔥</span>
          <div>
            <p className="font-semibold text-red-700">화재 감지됨</p>
            <p className="text-sm text-red-600">가장 가까운 출구로 이동하세요.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 탈출 경로 지도 */}
        <div className="bg-white rounded-lg shadow p-4 lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">나의 탈출 경로</h2>
          <div className="h-80 flex items-center justify-center border-2 border-dashed border-gray-200 rounded">
            <p className="text-gray-400">도면 위 탈출 경로 표시 (현재 위치 → 출구)</p>
            {/* TODO: 도면 위에 경로 하이라이트 */}
          </div>
        </div>

        {/* 안내 패널 */}
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">경로 정보</h3>
            <div className="space-y-2 text-sm">
              <p><span className="text-gray-500">목적지:</span> —</p>
              <p><span className="text-gray-500">거리:</span> —</p>
              <p><span className="text-gray-500">예상 시간:</span> —</p>
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">동료 SOS</h3>
            <button className="w-full py-3 bg-red-500 text-white font-bold rounded-lg hover:bg-red-600 transition">
              SOS 보내기
            </button>
            <p className="text-xs text-gray-400 mt-2 text-center">
              위험 시 주변 동료에게 도움 요청
            </p>
          </div>

          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold mb-2">근처 동료</h3>
            <p className="text-gray-400 text-sm">감지된 동료가 없습니다.</p>
            {/* TODO: 근처 동료 목록 + SOS 수신 표시 */}
          </div>
        </div>
      </div>
    </div>
  )
}
