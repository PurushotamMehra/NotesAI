import 'package:flutter/material.dart';

import '../models/note.dart';
import '../services/api_service.dart';
import '../theme/app_design.dart';
import 'memory_status_chips.dart';

Future<bool?> showNoteDetailSheet(
  BuildContext context,
  Note note, {
  ApiService? apiService,
}) {
  return showModalBottomSheet<bool>(
    context: context,
    backgroundColor: AppColors.background,
    isScrollControlled: true,
    useSafeArea: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
    ),
    builder: (context) {
      return NoteDetailSheet(
        note: note,
        apiService: apiService ?? ApiService(),
      );
    },
  );
}

class NoteDetailSheet extends StatefulWidget {
  const NoteDetailSheet({
    super.key,
    required this.note,
    required this.apiService,
  });

  final Note note;
  final ApiService apiService;

  @override
  State<NoteDetailSheet> createState() => _NoteDetailSheetState();
}

class _NoteDetailSheetState extends State<NoteDetailSheet> {
  late Note _note = widget.note;
  late final TextEditingController _editController;
  bool _isEditing = false;
  bool _isSaving = false;
  bool _isRetrying = false;
  bool _changed = false;

  @override
  void initState() {
    super.initState();
    _editController = TextEditingController(text: _note.rawInput);
  }

  @override
  void dispose() {
    _editController.dispose();
    super.dispose();
  }

  Future<void> _saveEdit() async {
    final rawInput = _editController.text.trim();
    if (rawInput.isEmpty || _isSaving) {
      return;
    }
    setState(() => _isSaving = true);
    try {
      final updated = await widget.apiService.updateNote(_note, rawInput);
      if (!mounted) return;
      setState(() {
        _note = updated;
        _editController.text = updated.rawInput;
        _isEditing = false;
        _changed = true;
      });
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  Future<void> _retry() async {
    if (_isRetrying) {
      return;
    }
    setState(() => _isRetrying = true);
    try {
      final updated = await widget.apiService.reprocessNote(_note);
      if (!mounted) return;
      setState(() {
        _note = updated;
        _editController.text = updated.rawInput;
        _changed = true;
      });
    } catch (error) {
      _showError(error);
    } finally {
      if (mounted) {
        setState(() => _isRetrying = false);
      }
    }
  }

  Future<void> _delete() async {
    if (_isSaving) {
      return;
    }
    setState(() => _isSaving = true);
    try {
      await widget.apiService.deleteNote(_note);
      if (mounted) {
        Navigator.of(context).pop(true);
      }
    } catch (error) {
      _showError(error);
      if (mounted) {
        setState(() => _isSaving = false);
      }
    }
  }

  void _showError(Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(error.toString())));
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.82,
      minChildSize: 0.45,
      maxChildSize: 0.94,
      builder: (context, scrollController) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(24, 18, 24, 24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'Memory · #${_note.id}',
                      style: AppTextStyles.sectionLabel,
                    ),
                  ),
                  MinimalIconButton(
                    icon: Icons.close,
                    tooltip: 'Close',
                    onPressed: () => Navigator.of(context).pop(_changed),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Expanded(
                child: ListView(
                  controller: scrollController,
                  children: [
                    Text(
                      _note.summary.isEmpty ? 'Untitled memory' : _note.summary,
                      style: AppTextStyles.screenTitle.copyWith(
                        fontSize: 28,
                        height: 1.18,
                      ),
                    ),
                    const SizedBox(height: 14),
                    MemoryStatusChips(
                      note: _note,
                      onRetry: _retry,
                      isRetrying: _isRetrying,
                    ),
                    if (_note.people.isNotEmpty || _note.topics.isNotEmpty) ...[
                      const SizedBox(height: 18),
                      Text(
                        [
                          if (_note.people.isNotEmpty)
                            'People: ${_note.people.join(', ')}',
                          if (_note.topics.isNotEmpty)
                            'Topics: ${_note.topics.join(', ')}',
                        ].join('\n'),
                        style: AppTextStyles.muted,
                      ),
                    ],
                    const SizedBox(height: 22),
                    if (_isEditing)
                      MinimalTextField(
                        controller: _editController,
                        hintText: 'Edit memory',
                        minLines: 6,
                        maxLines: 12,
                      )
                    else
                      Text(_note.cleanedNote, style: AppTextStyles.body),
                    if (_note.processingError.isNotEmpty ||
                        _note.embeddingError.isNotEmpty) ...[
                      const SizedBox(height: 18),
                      Text(
                        [
                          _note.processingError,
                          _note.embeddingError,
                        ].where((item) => item.isNotEmpty).join('\n'),
                        style: AppTextStyles.muted.copyWith(
                          color: AppColors.accent,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  TextButton(
                    onPressed: _isSaving
                        ? null
                        : () {
                            if (_isEditing) {
                              _saveEdit();
                            } else {
                              setState(() => _isEditing = true);
                            }
                          },
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.greenAccent,
                      textStyle: AppTextStyles.sectionLabel,
                    ),
                    child: Text(_isEditing ? 'SAVE' : 'EDIT'),
                  ),
                  if (_isEditing)
                    TextButton(
                      onPressed: _isSaving
                          ? null
                          : () {
                              _editController.text = _note.rawInput;
                              setState(() => _isEditing = false);
                            },
                      style: TextButton.styleFrom(
                        foregroundColor: AppColors.textSecondary,
                        textStyle: AppTextStyles.sectionLabel,
                      ),
                      child: const Text('CANCEL'),
                    ),
                  const Spacer(),
                  TextButton(
                    onPressed: _isSaving ? null : _delete,
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.accent,
                      textStyle: AppTextStyles.sectionLabel,
                    ),
                    child: const Text('DELETE'),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }
}
