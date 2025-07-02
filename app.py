from flask import Flask, render_template, request, jsonify
from datetime import datetime
from collections import deque
import os
from threading import Lock

app = Flask(__name__)

# storage
events_store = deque(maxlen=100)
events_lock = Lock()

# Statistics counters
event_counts = {
    'push': 0,
    'pull_request': 0,
    'merge': 0,
    'total': 0
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('X-GitHub-Event') == 'ping':
        return jsonify({'message': 'pong'}), 200

    event = request.headers.get('X-GitHub-Event')
    payload = request.json

    try:
        if event == 'push':
            process_push_event(payload)
        elif event == 'pull_request':
            process_pull_request_event(payload)
    except Exception as e:
        print(f"Error processing {event} event: {e}")
        return jsonify({'error': str(e)}), 500

    return jsonify({'message': 'Event received'}), 200

def process_push_event(payload):
    author = payload['pusher']['name']
    branch = payload['ref'].split('/')[-1]
    timestamp = datetime.now().strftime("%d %B %Y - %I:%M %p %Z")
    
    event_data = {
        'type': 'push',
        'author': author,
        'to_branch': branch,
        'timestamp': timestamp,
        'created_at': datetime.now().isoformat()
    }
    
    with events_lock:
        events_store.append(event_data)
        event_counts['push'] += 1
        event_counts['total'] += 1

def process_pull_request_event(payload):
    action = payload['action']
    if action not in ['opened', 'reopened', 'closed']:
        return
        
    author = payload['sender']['login']
    from_branch = payload['pull_request']['head']['ref']
    to_branch = payload['pull_request']['base']['ref']
    timestamp = datetime.now().strftime("%d %B %Y - %I:%M %p %Z")
    
    if action == 'closed' and payload['pull_request']['merged']:
        event_type = 'merge'
    else:
        event_type = 'pull_request'
    
    event_data = {
        'type': event_type,
        'author': author,
        'from_branch': from_branch,
        'to_branch': to_branch,
        'timestamp': timestamp,
        'created_at': datetime.now().isoformat()
    }
    
    with events_lock:
        events_store.append(event_data)
        event_counts[event_type] += 1
        event_counts['total'] += 1

@app.route('/api/events')
def get_events():
    with events_lock:
        events = list(events_store)
        return jsonify({
            'events': events,
            'counts': event_counts
        })

@app.route('/api/events/count')
def get_events_count():
    with events_lock:
        return jsonify({
            'count': event_counts['total'],
            'counts': event_counts
        })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)