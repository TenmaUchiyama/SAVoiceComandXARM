using UnityEngine;
using SA_XARM.SpatialRef.Data;

namespace SA_XARM.SpatialRef.Spatial
{
	public class SpatialObject : MonoBehaviour
	{
		[SerializeField] private string objectId;
		[SerializeField] private string objectLabel;
		[SerializeField] private string objectColor = "unknown";
		[SerializeField] private string objectShape = "unknown";
		[SerializeField] private string objectSize = "unknown";


		[SerializeField] private int x_grid = 0;
		[SerializeField] private int y_grid = 0;

		[SerializeField] private GameObject gridVisual;
		[SerializeField] private GameObject labelVisual;
		[SerializeField] private Color defaultColor = Color.white;
		[SerializeField] private Color highlightColor = Color.green;

		private Material matRenderer;
		private Renderer fallbackRenderer;

		public string Id => GetObjectId();
		public string Label => GetLabel();
		public string ColorName => GetColorName();
		public Vector3 Position => transform.position;
		public bool IsHighlighted { get; private set; }

		void Start()
		{
			if (gridVisual != null)
			{
				matRenderer = gridVisual.GetComponent<Renderer>().material;
			}
			else
			{
				fallbackRenderer = GetComponent<Renderer>();
				if (fallbackRenderer != null)
				{
					matRenderer = fallbackRenderer.material;
				}
			}

			if (string.IsNullOrWhiteSpace(objectLabel))
			{
				objectLabel = gameObject.name;
			}

			if (labelVisual != null)
			{
				labelVisual.SetActive(false);
			}

			SetRendererColor(defaultColor);
		}

		public void Initialize(ObjectData data)
		{
			if (data == null)
			{
				return;
			}

			objectId = data.id;
			objectLabel = data.label;
			objectColor = data.color;

			if (data.position != null)
			{
				transform.position = new Vector3(data.position.x, data.position.y, data.position.z);
			}
		}

		public void SetGridPosition(int x, int y)
		{
			x_grid = x;
			y_grid = y;
		}

		public void Highlight()
		{
			IsHighlighted = true;
			SetRendererColor(highlightColor);
		}

		public void Unhighlight()
		{
			IsHighlighted = false;
			SetRendererColor(defaultColor);
		}

		public void GazeHover()
		{
			Highlight();
		}

		public void GazeUnhover()
		{
			Unhighlight();
		}

		public void GazePinch()
		{
			SetRendererColor(Color.red);
		}

		public void GazeUnpinch()
		{
			SetRendererColor(Color.cyan);
		}

		public void ShowLabel(string overrideText = null)
		{
			if (labelVisual != null)
			{
				labelVisual.SetActive(true);
			}
		}

		public void HideLabel()
		{
			if (labelVisual != null)
			{
				labelVisual.SetActive(false);
			}
		}

		public (int, int) GetGridPosition()
		{
			return (x_grid, y_grid);
		}

		public string GetObjectId()
		{
			if (!string.IsNullOrWhiteSpace(objectId))
			{
				return objectId;
			}

			return gameObject.name;
		}

		public string GetLabel()
		{
			return string.IsNullOrWhiteSpace(objectLabel) ? gameObject.name : objectLabel;
		}

		public string GetColorName()
		{
			return string.IsNullOrWhiteSpace(objectColor) ? "unknown" : objectColor;
		}

		public string GetShape()
		{
			return string.IsNullOrWhiteSpace(objectShape) ? "unknown" : objectShape;
		}

		public string GetSizeName()
		{
			return string.IsNullOrWhiteSpace(objectSize) ? "unknown" : objectSize;
		}

		public string GetDirectionFrom(Vector3 viewerPosition, Vector3 viewerForward)
		{
			Vector3 toObject = Position - viewerPosition;
			toObject.y = 0f;

			if (toObject.sqrMagnitude < 0.0001f)
			{
				return "overlap";
			}

			Vector3 forward = viewerForward;
			forward.y = 0f;
			if (forward.sqrMagnitude < 0.0001f)
			{
				forward = Vector3.forward;
			}

			forward.Normalize();
			Vector3 right = Vector3.Cross(Vector3.up, forward).normalized;
			Vector3 direction = toObject.normalized;

			float forwardDot = Vector3.Dot(direction, forward);
			float rightDot = Vector3.Dot(direction, right);
			const float diagonalThreshold = 0.35f;

			if (forwardDot >= diagonalThreshold)
			{
				if (rightDot >= diagonalThreshold) return "front-right";
				if (rightDot <= -diagonalThreshold) return "front-left";
				return "front";
			}

			if (forwardDot <= -diagonalThreshold)
			{
				if (rightDot >= diagonalThreshold) return "back-right";
				if (rightDot <= -diagonalThreshold) return "back-left";
				return "back";
			}

			return rightDot >= 0f ? "right" : "left";
		}

		public float GetDistanceTo(Vector3 point)
		{
			return Vector3.Distance(Position, point);
		}

		public bool IsReachableBy(Vector3 robotPosition, float reachRadius)
		{
			if (reachRadius < 0f)
			{
				reachRadius = 0f;
			}

			return GetDistanceTo(robotPosition) <= reachRadius;
		}

		public ObjectData ToObjectData()
		{
			Vector3 position = Position;
			return new ObjectData
			{
				id = GetObjectId(),
				label = GetLabel(),
				color = GetColorName(),
				position = new Vec3(position.x, position.y, position.z)
			};
		}

		private void SetRendererColor(Color color)
		{
			if (matRenderer != null)
			{
				matRenderer.color = color;
			}
		}
	}
}