import json
from neo4j import GraphDatabase

# 请按实际环境修改
NEO4J_URI = "bolt://192.168.150.129:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "123456"
JSON_PATH = r"C:\Users\huanx\PyCharmMiscProject\hotpot_data.json"

def import_hotpot(uri, user, password, filepath):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)


    batch = []
    total = len(data)

    with driver.session() as session:
        for idx, item in enumerate(data):
            q_id = item.get('id', f'q_{idx}')
            question = item['question']
            answer = item.get('answer', '')
            q_type = item.get('type', '')
            level = item.get('level', '')

            # 预处理支持事实，转为排序后的列表
            ctx_titles = item['context']['title']
            sup_titles = item['supporting_facts']['title']
            sup_indices = item['supporting_facts']['sent_id']
            sup_positions = []
            for t, sid in zip(sup_titles, sup_indices):
                if t in ctx_titles:
                    doc_idx = ctx_titles.index(t)
                    sup_positions.append((doc_idx * 10000 + sid, t, sid))
            sup_positions.sort()

            # 整理当前问题的所有上下文句子
            sentences = []
            for doc_title, sents in zip(ctx_titles, item['context']['sentences']):
                for i, sent_text in enumerate(sents):
                    sentences.append((doc_title, i, sent_text))

            # 构建支持链边
            support_edges = []
            if len(sup_positions) >= 2:
                for i in range(len(sup_positions) - 1):
                    _, t1, s1 = sup_positions[i]
                    _, t2, s2 = sup_positions[i+1]
                    support_edges.append((t1, s1, t2, s2))

            batch.append({
                'q_id': q_id,
                'question': question,
                'answer': answer,
                'q_type': q_type,
                'level': level,
                'sentences': sentences,
                'support_edges': support_edges
            })

            # 每 200 条提交一次（可调整，过大可能触发内存问题）
            if len(batch) >= 200 or idx == total - 1:
                session.execute_write(_import_batch, batch)
                batch.clear()
                print(f"进度: {idx+1}/{total}")

    driver.close()
    print("导入完成！")

def _import_batch(tx, batch):
    # 用 UNWIND 批量处理
    query = """
    UNWIND $batch AS item

    // 创建问题
    MERGE (q:Question {id: item.q_id})
    SET q.text = item.question, q.answer = item.answer, q.type = item.q_type, q.level = item.level

    WITH item, q
    UNWIND item.sentences AS sent
    MERGE (d:Document {title: sent[0]})
    MERGE (q)-[:HAS_CONTEXT]->(d)
    MERGE (s:Sentence {doc_title: sent[0], index: sent[1]})
    SET s.text = sent[2]
    MERGE (d)-[:CONTAINS]->(s)

    // 构建支持边需要单独处理，因为需要引用已创建的节点
    """
    # 先批量创建问题和文档、句子（上面的查询可以完成）
    # 但支持边必须引用存在的节点，所以分开执行
    tx.run(query, batch=batch)

    # 再创建支持边
    edge_query = """
    UNWIND $batch AS item
    UNWIND item.support_edges AS edge
    MATCH (a:Sentence {doc_title: edge[0], index: edge[1]})
    MATCH (b:Sentence {doc_title: edge[2], index: edge[3]})
    MERGE (a)-[:SUPPORTS {q_id: item.q_id}]->(b)
    """
    tx.run(edge_query, batch=batch)

if __name__ == "__main__":
    import_hotpot(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, JSON_PATH)