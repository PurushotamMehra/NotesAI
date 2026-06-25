import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../theme/app_design.dart';

class AddNoteScreen extends StatefulWidget {
  const AddNoteScreen({super.key});

  @override
  State<AddNoteScreen> createState() => _AddNoteScreenState();
}

class _AddNoteScreenState extends State<AddNoteScreen> {
  final _controller = TextEditingController();
  final _apiService = ApiService();
  bool _isSaving = false;
  Map<String, dynamic>? _result;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final text = _controller.text.trim();
    if (text.isEmpty || _isSaving) {
      return;
    }

    setState(() {
      _isSaving = true;
      _error = null;
      _result = null;
    });

    try {
      final result = await _apiService.createNote(text);
      if (!mounted) return;
      setState(() {
        _result = result;
      });
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Memory saved')));
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          _isSaving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    return MinimalScaffold(
      title: 'NEW MEMORY',
      showBackButton: true,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          AppSpacing.page,
          34,
          AppSpacing.page,
          AppSpacing.page,
        ),
        children: [
          MinimalTextField(
            controller: _controller,
            minLines: 9,
            maxLines: 14,
            textInputAction: TextInputAction.newline,
            hintText: 'Write one thought...',
          ),
          const SizedBox(height: 18),
          Row(
            children: [
              TextButton(
                onPressed: _isSaving ? null : () => Navigator.of(context).pop(),
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.textSecondary,
                  textStyle: AppTextStyles.sectionLabel,
                ),
                child: const Text('CANCEL'),
              ),
              const Spacer(),
              TextButton(
                onPressed: _isSaving ? null : _submit,
                style: TextButton.styleFrom(
                  foregroundColor: AppColors.greenAccent,
                  textStyle: AppTextStyles.sectionLabel,
                ),
                child: Text(_isSaving ? 'SAVING' : 'SAVE'),
              ),
            ],
          ),
          if (_error != null) ...[
            const SizedBox(height: 18),
            SoftCard(
              color: AppColors.surfaceMuted,
              child: Text(_error!, style: AppTextStyles.muted),
            ),
          ],
          if (result != null) ...[
            const SizedBox(height: 28),
            const Text('SUMMARY', style: AppTextStyles.sectionLabel),
            const SizedBox(height: 10),
            Text(
              (result['summary'] ?? '').toString().isEmpty
                  ? 'No summary returned'
                  : result['summary'].toString(),
              style: AppTextStyles.body,
            ),
            const SizedBox(height: 22),
            _MetaLine(label: 'People', value: _joinList(result['people'])),
            _MetaLine(label: 'Topics', value: _joinList(result['topics'])),
          ],
        ],
      ),
    );
  }

  String _joinList(dynamic value) {
    final items = value is List ? value : const [];
    if (items.isEmpty) {
      return 'None';
    }
    return items.join(', ');
  }
}

class _MetaLine extends StatelessWidget {
  const _MetaLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Text('$label · $value', style: AppTextStyles.muted),
    );
  }
}
