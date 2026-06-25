import 'package:flutter/material.dart';

import '../models/note.dart';
import '../theme/app_design.dart';

class MemoryStatusChips extends StatelessWidget {
  const MemoryStatusChips({
    super.key,
    required this.note,
    this.onRetry,
    this.isRetrying = false,
  });

  final Note note;
  final VoidCallback? onRetry;
  final bool isRetrying;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        const _StatusChip(label: 'Saved', icon: Icons.check_circle_outline),
        if (note.isAiProcessed)
          const _StatusChip(label: 'AI processed', icon: Icons.auto_awesome)
        else
          _StatusChip(label: _processingLabel(note), icon: Icons.sync_problem),
        if (note.isSearchReady)
          const _StatusChip(label: 'Search ready', icon: Icons.manage_search)
        else if (note.embeddingStatus == 'failed')
          const _StatusChip(
            label: 'Search indexing failed',
            icon: Icons.error_outline,
            isWarning: true,
          )
        else
          const _StatusChip(label: 'Indexing', icon: Icons.hourglass_empty),
        if (note.needsRetry && onRetry != null)
          ActionChip(
            onPressed: isRetrying ? null : onRetry,
            avatar: isRetrying
                ? const SizedBox(
                    width: 14,
                    height: 14,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh, size: 16),
            label: const Text('Retry'),
            labelStyle: AppTextStyles.sectionLabel.copyWith(
              color: AppColors.greenAccent,
            ),
            backgroundColor: AppColors.surface,
            side: const BorderSide(color: AppColors.border),
          ),
      ],
    );
  }

  String _processingLabel(Note note) {
    if (note.processingStatus == 'fallback') {
      return 'AI fallback';
    }
    if (note.processingStatus == 'failed') {
      return 'AI failed';
    }
    return 'AI pending';
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.icon,
    this.isWarning = false,
  });

  final String label;
  final IconData icon;
  final bool isWarning;

  @override
  Widget build(BuildContext context) {
    final color = isWarning ? AppColors.accent : AppColors.greenAccent;
    return Chip(
      avatar: Icon(icon, size: 16, color: color),
      label: Text(label),
      labelStyle: AppTextStyles.sectionLabel.copyWith(color: color),
      backgroundColor: AppColors.surface,
      side: const BorderSide(color: AppColors.border),
      padding: EdgeInsets.zero,
    );
  }
}
