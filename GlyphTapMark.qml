import QtQuick
import QtQuick.Shapes

Item {
  id: root

  property color color: "white"
  property real strokeWidth: 2.4

  Shape {
    anchors.centerIn: parent
    width: 48
    height: 48
    scale: Math.min(root.width / width, root.height / height)

    ShapePath {
      fillColor: "transparent"
      strokeColor: root.color
      strokeWidth: root.strokeWidth
      capStyle: ShapePath.RoundCap
      joinStyle: ShapePath.RoundJoin

      PathSvg {
        path: "M42.5 34.376a8.119 8.119 0 1 1-16.238 0 8.119 8.119 0 0 1 16.238 0"
      }
    }

    ShapePath {
      fillColor: "transparent"
      strokeColor: root.color
      strokeWidth: root.strokeWidth
      capStyle: ShapePath.RoundCap
      joinStyle: ShapePath.RoundJoin

      PathSvg {
        path: "M29.456 6.459h9.85a2.687 2.687 0 0 1 2.687 2.687v9.85a2.687 2.687 0 0 1-2.687 2.687h-9.85a2.687 2.687 0 0 1-2.687-2.687v-9.85a2.687 2.687 0 0 1 2.687-2.687z"
      }
    }

    ShapePath {
      fillColor: "transparent"
      strokeColor: root.color
      strokeWidth: root.strokeWidth
      capStyle: ShapePath.RoundCap
      joinStyle: ShapePath.RoundJoin

      PathSvg {
        path: "m12.325 27.686-6.553 11.35A2.03 2.03 0 0 0 7.53 42.08h13.105a2.03 2.03 0 0 0 1.758-3.045L15.84 27.686a2.03 2.03 0 0 0-3.515 0m2.833-21.679a2.24 2.24 0 0 0 2.383.7c.834-.26 1.7.296 1.81 1.163a2.24 2.24 0 0 0 1.626 1.876 1.404 1.404 0 0 1 .894 1.958 2.24 2.24 0 0 0 .353 2.458c.583.65.436 1.67-.306 2.13a2.24 2.24 0 0 0-1.031 2.258 1.404 1.404 0 0 1-1.41 1.626 2.24 2.24 0 0 0-2.088 1.343c-.35.8-1.338 1.09-2.065.606a2.24 2.24 0 0 0-2.483 0 1.404 1.404 0 0 1-2.065-.606 2.24 2.24 0 0 0-2.089-1.343 1.404 1.404 0 0 1-1.409-1.626 2.24 2.24 0 0 0-1.031-2.259 1.404 1.404 0 0 1-.307-2.13 2.24 2.24 0 0 0 .354-2.457 1.404 1.404 0 0 1 .894-1.958A2.24 2.24 0 0 0 8.814 7.87a1.404 1.404 0 0 1 1.81-1.164 2.24 2.24 0 0 0 2.382-.7 1.406 1.406 0 0 1 2.152 0"
      }
    }
  }
}
