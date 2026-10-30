import sqlite3

conn = sqlite3.connect('vixor_local.db')
c = conn.cursor()
c.execute("INSERT INTO finding_scores (finding_id, risk_score, risk_class, model_version, features, shap_values, narrative, scored_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
          ('test-uuid', 75.0, 'medium', 'xgb-v1.0.0', '{"cvss_base": 7.5}', '{"cvss_base": 18.5}', 'test narrative', 'ml'))
conn.commit()
c.execute('SELECT * FROM finding_scores')
print('Rows:', c.fetchall())
conn.close()