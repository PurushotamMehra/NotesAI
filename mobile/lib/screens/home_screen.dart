import 'package:flutter/material.dart';

import '../theme/app_design.dart';
import 'add_note_screen.dart';
import 'chat_screen.dart';
import 'notes_screen.dart';
import 'search_screen.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return MinimalScaffold(
      title: 'SECOND BRAIN',
      actions: [
        MinimalIconButton(
          icon: Icons.search,
          tooltip: 'Search memories',
          onPressed: () => Navigator.of(
            context,
          ).push(MaterialPageRoute(builder: (_) => const SearchScreen())),
        ),
      ],
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.page,
          34,
          AppSpacing.page,
          AppSpacing.page,
        ),
        children: [
          SoftCard(
            onTap: () => _open(context, const AddNoteScreen()),
            padding: const EdgeInsets.fromLTRB(22, 24, 22, 90),
            child: Text(
              'Write one thought...',
              style: AppTextStyles.body.copyWith(
                color: AppColors.textSecondary,
              ),
            ),
          ),
          const SizedBox(height: 34),
          _HomeActionRow(
            title: 'Add memory',
            detail: 'now',
            onTap: () => _open(context, const AddNoteScreen()),
          ),
          _HomeActionRow(
            title: 'View memories',
            onTap: () => _open(context, const NotesScreen()),
          ),
          _HomeActionRow(
            title: 'Search memories',
            onTap: () => _open(context, const SearchScreen()),
          ),
          _HomeActionRow(
            title: 'Ask your notes',
            onTap: () => _open(context, const ChatScreen()),
          ),
        ],
      ),
    );
  }

  void _open(BuildContext context, Widget screen) {
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => screen));
  }
}

class _HomeActionRow extends StatelessWidget {
  const _HomeActionRow({required this.title, required this.onTap, this.detail});

  final String title;
  final String? detail;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 18),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  detail == null ? title : '$title · $detail',
                  style: AppTextStyles.body,
                ),
              ),
              const Icon(
                Icons.arrow_forward,
                size: 18,
                color: AppColors.textSecondary,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
