import 'package:flutter/material.dart';

import '../models/note.dart';
import '../services/api_service.dart';
import '../theme/app_design.dart';
import '../widgets/memory_status_chips.dart';
import '../widgets/note_detail_sheet.dart';

class NotesScreen extends StatefulWidget {
  const NotesScreen({super.key});

  @override
  State<NotesScreen> createState() => _NotesScreenState();
}

class _NotesScreenState extends State<NotesScreen> {
  final _apiService = ApiService();
  late Future<List<Note>> _notesFuture;

  @override
  void initState() {
    super.initState();
    _notesFuture = _apiService.fetchNotes();
  }

  void _reload() {
    setState(() {
      _notesFuture = _apiService.fetchNotes();
    });
  }

  @override
  Widget build(BuildContext context) {
    return MinimalScaffold(
      title: 'MEMORIES',
      showBackButton: true,
      actions: [
        MinimalIconButton(
          onPressed: _reload,
          tooltip: 'Refresh memories',
          icon: Icons.refresh,
        ),
      ],
      child: FutureBuilder<List<Note>>(
        future: _notesFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppColors.greenAccent,
              ),
            );
          }
          if (snapshot.hasError) {
            return _ErrorState(
              message: snapshot.error.toString(),
              onRetry: _reload,
            );
          }

          final notes = snapshot.data ?? [];
          if (notes.isEmpty) {
            return const Center(
              child: Text('No memories yet.', style: AppTextStyles.muted),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.page,
              26,
              AppSpacing.page,
              AppSpacing.page,
            ),
            itemCount: notes.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) {
              final note = notes[index];
              return _NoteCard(
                note: note,
                onTap: () async {
                  final changed = await showNoteDetailSheet(context, note);
                  if (changed == true) {
                    _reload();
                  }
                },
              );
            },
          );
        },
      ),
    );
  }
}

class _NoteCard extends StatelessWidget {
  const _NoteCard({required this.note, required this.onTap});

  final Note note;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final title = note.summary.isEmpty
        ? _firstSentence(note.cleanedNote)
        : note.summary;
    return SoftCard(
      onTap: onTap,
      padding: const EdgeInsets.fromLTRB(18, 16, 18, 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title.isEmpty ? 'Untitled memory' : title,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.body.copyWith(fontSize: 18),
          ),
          const SizedBox(height: 8),
          Text(
            note.cleanedNote,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.muted.copyWith(fontSize: 15),
          ),
          const SizedBox(height: 14),
          MemoryStatusChips(note: note),
          const SizedBox(height: 12),
          Text('Memory · #${note.id}', style: AppTextStyles.sectionLabel),
        ],
      ),
    );
  }

  String _firstSentence(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty) {
      return '';
    }
    final end = trimmed.indexOf('.');
    if (end == -1) {
      return trimmed;
    }
    return trimmed.substring(0, end + 1);
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.page),
        child: SoftCard(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                message,
                textAlign: TextAlign.center,
                style: AppTextStyles.muted,
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: onRetry,
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.greenAccent,
                  textStyle: AppTextStyles.sectionLabel,
                ),
                child: const Text('RETRY'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
