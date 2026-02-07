import os
import json
import re
import sys
from datetime import datetime

class CodebaseCartographer:
    def __init__(self, root_dir="."):
        self.root_dir = os.path.abspath(root_dir)
        self.nodes = []
        self.links = []
        self.stats = {
            "cpp": 0, "hpp": 0, "py": 0, "other": 0,
            "total_lines": 0, "file_count": 0
        }

    def scan(self):
        print(f"[*] Analyzing Silicon Structure at {self.root_dir}...")
        
        file_map = {}
        
        # 1. Walk the directory
        for root, dirs, files in os.walk(self.root_dir):
            if any(x in root for x in [".git", "__pycache__", ".pytest_cache", "build", "diag"]):
                continue
                
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), self.root_dir)
                ext = file.split('.')[-1].lower() if '.' in file else 'no_ext'
                
                # Update Stats
                self.stats["file_count"] += 1
                if ext in ["cpp", "c"]: self.stats["cpp"] += 1
                elif ext in ["hpp", "h"]: self.stats["hpp"] += 1
                elif ext == "py": self.stats["py"] += 1
                else: self.stats["other"] += 1

                # Node metadata
                size = os.path.getsize(os.path.join(root, file))
                node = {
                    "id": rel_path,
                    "name": file,
                    "group": self._get_group(ext),
                    "size": size,
                    "lines": self._count_lines(os.path.join(root, file))
                }
                self.nodes.append(node)
                file_map[rel_path] = node
                self.stats["total_lines"] += node["lines"]

        # 2. Analyze Connections (Static Dependency Extraction)
        for node in self.nodes:
            path = os.path.join(self.root_dir, node["id"])
            if node["id"].endswith(".py"):
                self._find_py_imports(node["id"], path)
            elif node["id"].endswith((".cpp", ".hpp")):
                self._find_cpp_includes(node["id"], path)

    def _get_group(self, ext):
        if ext in ["cpp", "c"]: return 1   # Logic/Services
        if ext in ["hpp", "h"]: return 2   # Core/Interfaces
        if ext == "py": return 3           # AI/Glue
        if ext == "json": return 4         # Config
        return 5                           # Other

    def _count_lines(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return len(f.readlines())
        except: return 0

    def _find_py_imports(self, source_id, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Find local imports like "from ai.shared_ring" or "import config_loader"
                imports = re.findall(r"(?:from|import)\s+([\w\.]+)", content)
                for imp in imports:
                    target = imp.replace('.', '/')
                    # Check for potential file matches
                    for node in self.nodes:
                        if target in node["id"]:
                            self.links.append({"source": source_id, "target": node["id"], "value": 1})
        except: pass

    def _find_cpp_includes(self, source_id, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                includes = re.findall(r'#include\s+["<]([\w\./\\]+)[">]', content)
                for inc in includes:
                    target = inc.replace('\\', '/')
                    for node in self.nodes:
                        if target in node["id"]:
                            self.links.append({"source": source_id, "target": node["id"], "value": 2})
        except: pass

    def generate_html(self, output_path="CODEBASE_MAP.html"):
        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>OMAP // Codebase Cartography</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #050508;
            --panel: rgba(15, 20, 30, 0.85);
            --accent: #00ff41;
            --data: #00ffff;
            --ai: #ff00ff;
        }}
        body {{
            background-color: var(--bg);
            color: white;
            font-family: 'JetBrains Mono', monospace;
            margin: 0;
            overflow: hidden;
            background-image: radial-gradient(circle at 2px 2px, rgba(0, 255, 65, 0.05) 1px, transparent 0);
            background-size: 40px 40px;
        }}
        header {{
            position: absolute;
            top: 0; left: 0; right: 0;
            padding: 20px;
            background: linear-gradient(to bottom, rgba(0,0,0,0.8), transparent);
            z-index: 100;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0,255,65,0.2);
        }}
        .logo {{
            font-family: 'Orbitron', sans-serif;
            font-size: 24px;
            letter-spacing: 4px;
            color: var(--accent);
            text-shadow: 0 0 10px var(--accent);
        }}
        #graph-container {{
            width: 100vw;
            height: 100vh;
        }}
        .panel {{
            position: absolute;
            background: var(--panel);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 15px;
            pointer-events: all;
        }}
        #stats-panel {{
            top: 80px; left: 20px;
            width: 300px;
        }}
        #info-panel {{
            bottom: 20px; right: 20px;
            width: 350px;
            min-height: 100px;
        }}
        .stat-row {{
            display: flex; justify-content: space-between; margin-bottom: 5px;
            font-size: 12px; border-bottom: 1px solid rgba(255,255,255,0.05);
        }}
        .stat-val {{ color: var(--accent); }}
        h2 {{ font-family: 'Orbitron'; font-size: 14px; margin-top: 0; color: var(--data); text-transform: uppercase; }}
        .node {{ stroke: #fff; stroke-width: 1.5px; cursor: pointer; transition: 0.3s; }}
        .link {{ stroke: rgba(255,255,255,0.1); stroke-opacity: 0.6; }}
        .label {{ font-size: 10px; fill: rgba(255,255,255,0.5); pointer-events: none; }}
    </style>
</head>
<body>
    <header>
        <div class="logo">ULTRAMAGIC // OMAP v1.0</div>
        <div style="font-size: 10px; opacity: 0.5;">GENERATED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    </header>

    <div id="graph-container"></div>

    <div id="stats-panel" class="panel">
        <h2>System Architecture</h2>
        <div class="stat-row"><span>Total Files</span><span class="stat-val">{self.stats['file_count']}</span></div>
        <div class="stat-row"><span>Logic Lines</span><span class="stat-val">{self.stats['total_lines']}</span></div>
        <div style="height: 200px; margin-top: 20px;">
            <canvas id="typeChart"></canvas>
        </div>
    </div>

    <div id="info-panel" class="panel">
        <h2>Entity Inspector</h2>
        <div id="inspector-content" style="font-size: 12px; color: #aaa;">
            Hover over a node to analyze its silicon properties.
        </div>
    </div>

    <script>
        const data = {{
            nodes: {json.dumps(self.nodes)},
            links: {json.dumps(self.links)}
        }};

        const width = window.innerWidth;
        const height = window.innerHeight;

        const svg = d3.select("#graph-container")
            .append("svg")
            .attr("width", width)
            .attr("height", height);

        const simulation = d3.forceSimulation(data.nodes)
            .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-200))
            .force("center", d3.forceCenter(width / 2, height / 2));

        const link = svg.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(data.links)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke-width", d => Math.sqrt(d.value));

        const node = svg.append("g")
            .attr("class", "nodes")
            .selectAll("circle")
            .data(data.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", d => Math.sqrt(d.size / 100) + 5)
            .attr("fill", d => {{
                if (d.group === 1) return "#00ff41";
                if (d.group === 2) return "#00ffff";
                if (d.group === 3) return "#ff00ff";
                return "#888";
            }})
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended))
            .on("mouseover", (e, d) => {{
                d3.select("#inspector-content").html(`
                    <div style="color:#fff; font-weight:bold; margin-bottom:5px;">FILE:${{d.id}}</div>
                    <div class="stat-row"><span>Type:</span><span class="stat-val">${{d.group === 1 ? 'Service' : d.group === 3 ? 'AI Core' : 'Kernel'}}</span></div>
                    <div class="stat-row"><span>Size:</span><span class="stat-val">${{d.size}} bytes</span></div>
                    <div class="stat-row"><span>Lines:</span><span class="stat-val">${{d.lines}}</span></div>
                `);
            }});

        const labels = svg.append("g")
            .selectAll("text")
            .data(data.nodes)
            .enter().append("text")
            .attr("class", "label")
            .text(d => d.name);

        simulation.on("tick", () => {{
            link.attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);

            node.attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            labels.attr("x", d => d.x + 12)
                  .attr("y", d => d.y + 3);
        }});

        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
        }}
        function dragged(event, d) {{
            d.fx = event.x; d.fy = event.y;
        }}
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null; d.fy = null;
        }}

        // Charts
        new Chart(document.getElementById('typeChart'), {{
            type: 'doughnut',
            data: {{
                labels: ['C++', 'Headers', 'Python', 'Config'],
                datasets: [{{
                    data: [{self.stats['cpp']}, {self.stats['hpp']}, {self.stats['py']}, {self.stats['other']}],
                    backgroundColor: ['#00ff41', '#00ffff', '#ff00ff', '#444'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                plugins: {{ legend: {{ labels: {{ color: '#fff', font: {{ size: 10 }} }} }} }},
                maintainAspectRatio: false
            }}
        }});
    </script>
</body>
</html>
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        print(f"[+] OMAP Success: Map exported to {output_path}")

if __name__ == "__main__":
    mapper = CodebaseCartographer()
    mapper.scan()
    mapper.generate_html()
