void BoundingBoxConvert_float(
    float3 Position, // モデルの頂点座標
    float3 BoundingMin, // バウンディングボックスの最小座標
    float3 BoundingMax, // バウンディングボックスの最大座標
    out float3 Output // 変換後の頂点座標
    ) 
{
    // モデル頂点のy座標が 0 ~ 1 の範囲に収まるように座標変換
    float y = (Position.y - BoundingMin.y) / (BoundingMax.y - BoundingMin.y);

    // バウンディングボックスを四角錐に変形
    float2 centerXZ = (BoundingMin.xz + BoundingMax.xz) / 2.0; // 中心座標
    Position.xz = lerp(Position.xz, centerXZ, y); // yが1に近づくにつれて、XZ座標は中心座標に近づく

    // 変換後の頂点を出力
    Output = Position;
}