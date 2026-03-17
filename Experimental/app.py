import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle

# =========================
# 入力データ例
# =========================
objects = [
    {"object_id": 1, "color": "red",    "relative_x": -0.25, "relative_y":  0.55},
    {"object_id": 2, "color": "blue",   "relative_x":  0.00, "relative_y":  0.55},
    {"object_id": 3, "color": "green",  "relative_x":  0.25, "relative_y":  0.55},
    {"object_id": 4, "color": "yellow", "relative_x": -0.12, "relative_y":  0.28},
    {"object_id": 5, "color": "purple", "relative_x":  0.12, "relative_y":  0.28},
    {"object_id": 6, "color": "orange", "relative_x": -0.32, "relative_y":  0.00},
    {"object_id": 7, "color": "gray",   "relative_x":  0.03, "relative_y": -0.05},
]

# =========================
# 設定
# =========================
FIG_W, FIG_H = 8, 6
OBJECT_RADIUS = 0.08
USER_POS = (0.0, -0.55)
ROBOT_POS = (-0.75, 0.40)

# y軸を「上が奥」に見せたいならそのまま
# もし手前/奥の定義上、逆にしたければここで反転
FLIP_Y = False


def transform_point(x: float, y: float) -> tuple[float, float]:
    if FLIP_Y:
        y = -y
    return x, y


def draw_robot(ax, center_x: float, center_y: float, width: float = 0.18, height: float = 0.42):

    # 三角形っぽい内部
    tri = Polygon(
        [
            (center_x - width / 2, center_y + height / 2),
            (center_x + width / 2, center_y),
            (center_x - width / 2, center_y - height / 2),
        ],
        closed=True, fill=False, edgecolor="gray", linewidth=1.0
    )
    ax.add_patch(tri)

    ax.text(center_x - 0.01, center_y, "Robot", rotation=270,
            ha="center", va="center", fontsize=14)


def draw_user(ax, center_x: float, center_y: float, width: float = 0.22, height: float = 0.18):
    tri = Polygon(
        [
            (center_x, center_y + height / 2),
            (center_x - width / 2, center_y - height / 2),
            (center_x + width / 2, center_y - height / 2),
        ],
        closed=True, fill=False, edgecolor="gray", linewidth=1.0
    )
    ax.add_patch(tri)

    ax.text(center_x, center_y - 0.01, "User", ha="center", va="center", fontsize=14)


def draw_objects(ax, objects_data):
    for obj in objects_data:
        x, y = transform_point(obj["relative_x"], obj["relative_y"])

        circle = Circle(
            (x, y),
            radius=OBJECT_RADIUS,
            facecolor="#f0f0f0",
            edgecolor="gray",
            linewidth=0.9
        )
        ax.add_patch(circle)

        ax.text(
            x, y, str(obj["object_id"]),
            ha="center", va="center",
            fontsize=14, fontweight="bold"
        )


def auto_limits(objects_data, user_pos, robot_pos, margin=0.18):
    xs = [obj["relative_x"] for obj in objects_data] + [user_pos[0], robot_pos[0]]
    ys = [obj["relative_y"] for obj in objects_data] + [user_pos[1], robot_pos[1]]

    if FLIP_Y:
        ys = [-y for y in ys]

    return (
        min(xs) - margin, max(xs) + margin,
        min(ys) - margin, max(ys) + margin
    )


def make_diagram(objects_data):
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H))

    # オブジェクト
    draw_objects(ax, objects_data)

    # Robot
    robot_x, robot_y = transform_point(*ROBOT_POS)
    draw_robot(ax, robot_x, robot_y)

    # User
    user_x, user_y = transform_point(*USER_POS)
    draw_user(ax, user_x, user_y)

    # 見た目調整
    xmin, xmax, ymin, ymax = auto_limits(objects_data, USER_POS, ROBOT_POS)
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_aspect("equal")
    ax.axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    make_diagram(objects)