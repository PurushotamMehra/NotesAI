import 'package:flutter/material.dart';

class NotesListScreen extends StatelessWidget {
  const NotesListScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: const [_EmptyNotesState()],
    );
  }
}

class _EmptyNotesState extends StatelessWidget {
  const _EmptyNotesState();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 48),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.library_books_outlined,
              size: 48,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 12),
            Text(
              'No notes yet',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      ),
    );
  }
}
