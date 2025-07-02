from flask import Flask, json, request, jsonify, render_template
from datetime import datetime
from collections import deque
from threading import Lock

app = Flask(__name__)

# In-memory storage
events_store = deque(maxlen=100)
events_lock = Lock()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def api_github_webhook():
    if request.headers['Content-Type'] != 'application/json':
        return jsonify({'error': 'Invalid content type'}), 400
    
    # Debug print
    print("GitHub Payload:", json.dumps(request.json, indent=2))
    
    event_type = request.headers.get('X-GitHub-Event')
    
    if event_type == 'ping':
        return jsonify({'message': 'pong'}), 200
    
    try:
        if event_type == 'push':
            return process_push_event(request.json)
        elif event_type == 'pull_request':
            return process_pull_request_event(request.json)
    except Exception as e:
        print(f"Processing error: {str(e)}")
        return jsonify({'error': str(e)}), 500

def process_push_event(payload):
    event_data = {
        'type': 'push',
        'author': payload['pusher']['name'],
        'branch': payload['ref'].split('/')[-1],
        'timestamp': datetime.now().isoformat(),
        'message': f"{payload['pusher']['name']} pushed to {payload['ref'].split('/')[-1]}"
    }
    
    with events_lock:
        events_store.append(event_data)
    
    return jsonify(event_data), 200

def process_pull_request_event(payload):
    action = payload['action']
    if action == 'closed' and payload['pull_request']['merged']:
        event_type = 'merge'
        message = f"{payload['sender']['login']} merged to {payload['pull_request']['base']['ref']}"
    else:
        event_type = 'pull_request'
        message = f"{payload['sender']['login']} opened PR to {payload['pull_request']['base']['ref']}"
    
    event_data = {
        'type': event_type,
        'author': payload['sender']['login'],
        'from_branch': payload['pull_request']['head']['ref'],
        'to_branch': payload['pull_request']['base']['ref'],
        'timestamp': datetime.now().isoformat(),
        'message': message
    }
    
    with events_lock:
        events_store.append(event_data)
    
    return jsonify(event_data), 200

@app.route('/api/events')
def get_events():
    with events_lock:
        return jsonify({'events': list(events_store)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)