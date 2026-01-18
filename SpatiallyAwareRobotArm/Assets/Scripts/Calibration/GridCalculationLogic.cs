using UnityEngine;
using System.Collections.Generic;



namespace SA_XARM.Calibration{ // 計算ロジックのみを担当するクラス
public class GridCalculationLogic
{
    /// <summary>
    /// 3点（原点、X軸端、Y軸端）から格子点リストを生成する
    /// </summary>
    public static List<GridPointData> GenerateGridPoints(
        Vector3 origin, 
        Vector3 xEnd, 
        Vector3 yEnd, 
        int rows, 
        int cols,
        Matrix4x4 worldToAnchor)
    {
        var points = new List<GridPointData>();

        // 1マスあたりのベクトルを計算
        // (rows - 1) で割ることで、端から端までを等分する
        Vector3 stepX = (cols > 1) ? (xEnd - origin) / (cols - 1) : Vector3.zero;
        Vector3 stepY = (rows > 1) ? (yEnd - origin) / (rows - 1) : Vector3.zero;

        int index = 0;
        for (int r = 0; r < rows; r++)
        {
            for (int c = 0; c < cols; c++)
            {
                // ワールド座標での計算
                Vector3 worldPos = origin + (stepX * c) + (stepY * r);

                // ローカル座標（アンカー基準）に変換
                Vector3 localPos = worldToAnchor.MultiplyPoint3x4(worldPos);

                points.Add(new GridPointData 
                { 
                    id = index, 
                    localPos = localPos 
                });

                index++;
            }
        }

        return points;
    }

    /// <summary>
    /// 原点とX軸方向から、基準となる座標系（逆行列）を作成する
    /// </summary>
    public static Matrix4x4 CalculateAnchorMatrix(Vector3 origin, Vector3 xTarget)
    {
        Vector3 forward = (xTarget - origin).normalized;
        Vector3 up = Vector3.up; 
        Vector3 right = Vector3.Cross(up, forward).normalized; // 仮の右
        Vector3 correctUp = Vector3.Cross(forward, right).normalized; // 補正された上

        Quaternion rotation = Quaternion.LookRotation(forward, correctUp);
        
        // World -> Local の変換行列
        return Matrix4x4.TRS(origin, rotation, Vector3.one).inverse;
    }

    /// <summary>
    /// 3点（原点、X軸端、Y軸端）から、基準となる座標系（逆行列）を作成する
    /// </summary>
    public static Matrix4x4 CalculateAnchorMatrix(Vector3 origin, Vector3 xTarget, Vector3 yTarget)
    {
        Vector3 xAxis = (xTarget - origin).normalized;
        Vector3 yAxis = (yTarget - origin).normalized;

        // Z軸は平面の法線（右手系: x × y = z）
        Vector3 zAxis = Vector3.Cross(xAxis, yAxis);
        if (zAxis.sqrMagnitude < 1e-8f)
        {
            // 3点がほぼ一直線などで平面が定義できない場合は、既存ロジックへフォールバック
            return CalculateAnchorMatrix(origin, xTarget);
        }

        zAxis.Normalize();
        // 直交化（Gram-Schmidt）: y を z と x に直交させる
        yAxis = Vector3.Cross(zAxis, xAxis).normalized;

        // Anchor(Local) -> World 行列を列ベクトルで構成し、逆行列で World -> Anchor を得る
        Matrix4x4 anchorToWorld = Matrix4x4.identity;
        anchorToWorld.SetColumn(0, new Vector4(xAxis.x, xAxis.y, xAxis.z, 0f));
        anchorToWorld.SetColumn(1, new Vector4(yAxis.x, yAxis.y, yAxis.z, 0f));
        anchorToWorld.SetColumn(2, new Vector4(zAxis.x, zAxis.y, zAxis.z, 0f));
        anchorToWorld.SetColumn(3, new Vector4(origin.x, origin.y, origin.z, 1f));

        return anchorToWorld.inverse;
    }
}
}