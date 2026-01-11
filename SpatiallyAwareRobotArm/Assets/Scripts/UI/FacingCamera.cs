using System.Collections;
using System.Collections.Generic;
using UnityEngine;

public class FacingCamera : MonoBehaviour
{
    // Start is called before the first frame update
    void Start()
    {
        
    }

    // Update is called once per frame
void Update()
{
    if (Camera.main == null) return;

    // 1. 自分の位置からカメラの位置への方向ベクトルを計算
    Vector3 targetDirection = Camera.main.transform.position - transform.position;

    // 2. Y成分を0にする（これで上下の傾きと、頭の左右の傾き（Roll）を無視できる）
    targetDirection.y = 0;

    // 3. 方向がゼロでない場合のみ回転を適用
    if (targetDirection != Vector3.zero)
    {
        // 4. LookRotationでその方向を向かせる
        // ※Canvasの正面が裏返る場合は、-targetDirection にしてください
        transform.rotation = Quaternion.LookRotation(-targetDirection);
    }
}
}
