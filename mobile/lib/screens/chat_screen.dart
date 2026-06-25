import 'package:flutter/material.dart';

import '../models/note.dart';
import '../services/api_service.dart';
import '../theme/app_design.dart';
import '../widgets/note_detail_sheet.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _apiService = ApiService();
  final List<_ChatMessage> _messages = [];
  int? _sessionId;
  bool _isSending = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final query = _controller.text.trim();
    if (query.isEmpty || _isSending) {
      return;
    }

    setState(() {
      _messages.add(_ChatMessage(text: query, isUser: true));
      _controller.clear();
      _isSending = true;
    });

    try {
      final result = await _apiService.chat(query, sessionId: _sessionId);
      final sources = result['sources'] is List
          ? (result['sources'] as List)
                .whereType<Map<String, dynamic>>()
                .map(Note.fromJson)
                .toList()
          : const <Note>[];
      if (!mounted) return;
      setState(() {
        _sessionId = int.tryParse(result['session_id']?.toString() ?? '');
        _messages.add(
          _ChatMessage(
            text: (result['answer'] ?? '').toString(),
            isUser: false,
            sources: sources,
          ),
        );
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _messages.add(_ChatMessage(text: error.toString(), isUser: false));
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return MinimalScaffold(
      title: 'ASK MEMORY',
      showBackButton: true,
      bottom: _ChatInput(
        controller: _controller,
        isSending: _isSending,
        onSend: _send,
      ),
      child: _messages.isEmpty
          ? const Center(
              child: Text('Ask your notes', style: AppTextStyles.body),
            )
          : ListView.builder(
              padding: const EdgeInsets.fromLTRB(
                AppSpacing.page,
                26,
                AppSpacing.page,
                AppSpacing.page,
              ),
              itemCount: _messages.length,
              itemBuilder: (context, index) => _MessageBubble(
                message: _messages[index],
                onOpenSource: (note) =>
                    showNoteDetailSheet(context, note, apiService: _apiService),
              ),
            ),
    );
  }
}

class _ChatInput extends StatelessWidget {
  const _ChatInput({
    required this.controller,
    required this.isSending,
    required this.onSend,
  });

  final TextEditingController controller;
  final bool isSending;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 8, 18, 18),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isSending)
            const LinearProgressIndicator(
              minHeight: 1,
              color: AppColors.greenAccent,
              backgroundColor: AppColors.border,
            ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: MinimalTextField(
                  controller: controller,
                  hintText: 'Ask a question',
                  textInputAction: TextInputAction.send,
                  onSubmitted: (_) => onSend(),
                ),
              ),
              const SizedBox(width: 10),
              Material(
                color: AppColors.textPrimary,
                shape: const CircleBorder(),
                child: IconButton(
                  onPressed: isSending ? null : onSend,
                  tooltip: 'Send',
                  color: AppColors.surface,
                  disabledColor: AppColors.textSecondary,
                  icon: const Icon(Icons.arrow_forward),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ChatMessage {
  const _ChatMessage({
    required this.text,
    required this.isUser,
    this.sources = const [],
  });

  final String text;
  final bool isUser;
  final List<Note> sources;
}

class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message, required this.onOpenSource});

  final _ChatMessage message;
  final ValueChanged<Note> onOpenSource;

  @override
  Widget build(BuildContext context) {
    final visibleSources = message.sources
        .where((source) => _sourceText(source).isNotEmpty)
        .toList();
    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.78,
        ),
        child: Padding(
          padding: const EdgeInsets.only(bottom: 14),
          child: DecoratedBox(
            decoration: BoxDecoration(
              color: message.isUser
                  ? const Color(0xFFEFE7DC)
                  : AppColors.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(
                color: message.isUser
                    ? const Color(0xFFE1D1BE)
                    : AppColors.border,
              ),
            ),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(message.text, style: AppTextStyles.body),
                  if (!message.isUser && visibleSources.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    const Text('Sources', style: AppTextStyles.sectionLabel),
                    const SizedBox(height: 8),
                    for (final source in visibleSources.take(4))
                      _SourceLine(
                        label: _sourceLabel(source),
                        onTap: () => onOpenSource(source),
                      ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  String _sourceLabel(Note source) {
    final noteId = source.id.toString();
    return '#$noteId · ${_sourceText(source)}';
  }

  String _sourceText(Note source) {
    if (source.summary.trim().isNotEmpty) {
      return source.summary.trim();
    }
    if (source.cleanedNote.trim().isNotEmpty) {
      return source.cleanedNote.trim();
    }
    return source.rawInput.trim();
  }
}

class _SourceLine extends StatelessWidget {
  const _SourceLine({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(10),
        child: Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 6),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: AppColors.surfaceMuted,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Text(
            label,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: AppTextStyles.muted.copyWith(fontSize: 13),
          ),
        ),
      ),
    );
  }
}
