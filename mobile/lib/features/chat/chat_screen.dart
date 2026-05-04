import 'package:flutter/material.dart';

class ChatScreen extends StatelessWidget {
  const ChatScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          Expanded(
            child: Center(
              child: Text(
                'Chat is not connected yet',
                style: Theme.of(context).textTheme.titleMedium,
              ),
            ),
          ),
          TextField(
            enabled: false,
            decoration: InputDecoration(
              hintText: 'Ask your notes',
              suffixIcon: IconButton(
                onPressed: null,
                tooltip: 'Send',
                icon: const Icon(Icons.send_outlined),
              ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
