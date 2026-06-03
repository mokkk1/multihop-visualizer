from flask import Flask, request, jsonify, render_template
from neo4j import GraphDatabase

app = Flask(__name__)
driver = GraphDatabase.driver("bolt://192.168.150.129:7687", auth=("neo4j", "123456"))  # 请替换为实际密码

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/search')
def search():
    q = request.args.get('q', '')
    with driver.session() as session:
        result = session.run("""
            MATCH (n)
            WHERE (n:Question AND n.text CONTAINS $q)
               OR (n:Sentence AND n.text CONTAINS $q)
            RETURN n.id AS id, n.text AS text, labels(n) AS labels LIMIT 20
        """, q=q)
        data = []
        for rec in result:
            data.append({
                'id': rec['id'],
                'text': rec['text'][:120],
                'type': rec['labels'][0]
            })
        return jsonify(data)

@app.route('/api/examples')
def examples():
    with driver.session() as session:
        result = session.run("""
            MATCH (q:Question)
            RETURN q.id AS id, q.text AS text
            ORDER BY rand()
            LIMIT 5
        """)
        data = [{'id': rec['id'], 'text': rec['text'][:100]} for rec in result]
        return jsonify(data)

@app.route('/api/chain')
def chain():
    q_id = request.args.get('id')
    if not q_id:
        return jsonify({'error': 'id required'}), 400

    with driver.session() as session:
        result = session.run("""
            MATCH (q:Question {id: $q_id})
            OPTIONAL MATCH (q)-[:HAS_CONTEXT]->(d:Document)-[:CONTAINS]->(s:Sentence)
            WITH q, s
            WHERE EXISTS { MATCH (s)-[:SUPPORTS {q_id: $q_id}]->() }
               OR EXISTS { MATCH ()-[:SUPPORTS {q_id: $q_id}]->(s) }
            WITH q, collect(DISTINCT s) AS sents
            OPTIONAL MATCH path = (s1:Sentence)-[:SUPPORTS {q_id: $q_id}]->(s2:Sentence)
            WHERE s1 IN sents AND s2 IN sents
            RETURN sents, collect(path) AS paths, q.answer AS answer, q.text AS question
        """, q_id=q_id)
        rec = result.single()
        if not rec:
            return jsonify({'error': 'question not found'}), 404

        nodes = []
        edges = []
        node_ids = set()

        doc_colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
            '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9'
        ]
        doc_color_map = {}
        color_idx = 0
        for s in rec['sents']:
            doc = s['doc_title']
            if doc not in doc_color_map:
                doc_color_map[doc] = doc_colors[color_idx % len(doc_colors)]
                color_idx += 1
            nid = doc + '::' + str(s['index'])
            if nid not in node_ids:
                node_ids.add(nid)
                nodes.append({
                    'id': nid,
                    'label': s['text'][:80],
                    'title': s['text'],
                    'group': 'sentence',
                    'color': doc_color_map[doc],
                    'shape': 'dot',
                    'size': 20
                })

        for p in rec['paths']:
            if p:
                start = p.start_node['doc_title'] + '::' + str(p.start_node['index'])
                end = p.end_node['doc_title'] + '::' + str(p.end_node['index'])
                edges.append({
                    'from': start,
                    'to': end,
                    'label': '支持',
                    'arrows': 'to',
                    'width': 3,
                    'color': {'color': '#2C3E50', 'opacity': 0.8}
                })

        nodes.append({
            'id': q_id,
            'label': '❓ ' + (rec['question'] or '')[:60],
            'title': 'Answer: ' + (rec['answer'] or '未知'),
            'group': 'question',
            'color': '#FFD700',
            'shape': 'star',
            'size': 35,
            'font': {'size': 16, 'face': 'Microsoft YaHei', 'color': '#000000', 'bold': True}
        })

        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'answer': rec['answer']
        })

@app.route('/api/cluster')
def cluster():
    with driver.session() as session:
        result = session.run("""
            MATCH (d:Document)<-[:HAS_CONTEXT]-(q:Question)
            WITH d, count(q) AS qcnt
            RETURN d.title AS title, qcnt
            ORDER BY qcnt DESC LIMIT 100
        """)
        clusters = {}
        for rec in result:
            bucket = rec['qcnt'] // 5
            if bucket not in clusters:
                clusters[bucket] = {'cluster_id': bucket, 'documents': [], 'count': 0}
            clusters[bucket]['documents'].append(rec['title'])
            clusters[bucket]['count'] += 1
        return jsonify(list(clusters.values()))

if __name__ == '__main__':
    app.run(debug=True, port=5000)