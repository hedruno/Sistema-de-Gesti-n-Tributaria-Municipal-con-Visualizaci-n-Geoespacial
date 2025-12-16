class KDTree {
  constructor(points, depth = 0) {
    if (!points.length) {
      this.node = null;
      return;
    }

    const k = 2; // latitud, longitud
    const axis = depth % k;

    points.sort((a, b) => a[axis] - b[axis]);
    const median = Math.floor(points.length / 2);

    this.node = points[median];
    this.left = new KDTree(points.slice(0, median), depth + 1);
    this.right = new KDTree(points.slice(median + 1), depth + 1);
  }

  nearest(point, best = null, depth = 0) {
    if (!this.node) return best;

    const k = 2;
    const axis = depth % k;

    let nextBranch = point[axis] < this.node[axis] ? this.left : this.right;
    let otherBranch = point[axis] < this.node[axis] ? this.right : this.left;

    best = nextBranch.nearest(point, best, depth + 1) || this.node;

    const dist = (a, b) => Math.sqrt((a[0]-b[0])**2 + (a[1]-b[1])**2);
    if (!best || dist(point, this.node) < dist(point, best)) best = this.node;

    if (Math.abs(point[axis] - this.node[axis]) < dist(point, best)) {
      best = otherBranch.nearest(point, best, depth + 1) || best;
    }

    return best;
  }

  // Buscar un punto exacto (o dentro de una tolerancia) en el KD-Tree.
  // Devuelve el nodo encontrado (array [x,y]) o null si no existe.
  // Uso: tree.find([lat, lng])
  find(point, depth = 0, epsilon = 1e-9) {
    if (!this.node) return null;

    const axis = depth % 2;
    const [px, py] = point;
    const [nx, ny] = this.node;

    // comprobar igualdad aproximada
    const equal = (Math.abs(px - nx) <= epsilon) && (Math.abs(py - ny) <= epsilon);
    if (equal) return this.node;

    // decidir rama a visitar
    if (point[axis] < this.node[axis]) {
      return this.left ? this.left.find(point, depth + 1, epsilon) : null;
    } else {
      return this.right ? this.right.find(point, depth + 1, epsilon) : null;
    }
  }
}
