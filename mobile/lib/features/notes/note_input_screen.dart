import 'package:flutter/material.dart';

class NoteInputScreen extends StatelessWidget {
  const NoteInputScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        TextField(
          minLines: 5,
          maxLines: 8,
          decoration: InputDecoration(
            labelText: 'Capture a note',
            hintText: 'Write what you want to remember',
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
          ),
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            IconButton.filledTonal(
              onPressed: null,
              tooltip: 'Voice',
              icon: const Icon(Icons.mic_none),
            ),
            const SizedBox(width: 8),
            IconButton.filledTonal(
              onPressed: null,
              tooltip: 'Image',
              icon: const Icon(Icons.image_outlined),
            ),
            const SizedBox(width: 8),
            IconButton.filledTonal(
              onPressed: null,
              tooltip: 'Link',
              icon: const Icon(Icons.link),
            ),
            const Spacer(),
            FilledButton.icon(
              onPressed: null,
              icon: const Icon(Icons.check),
              label: const Text('Save'),
            ),
          ],
        ),
      ],
    );
  }
}
